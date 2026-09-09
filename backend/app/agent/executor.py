"""The agent loop and the execution-time risk gate.

This is what makes KINTIX *agentic*: given a Pre-Approved blueprint, the agent
plans, calls tools, reads the results and loops — deciding its own next action —
until the work is done. Given a Human-in-the-Loop blueprint it does the same,
but the gate stops it at the first consequential write. Given a Too-Risky
process it never starts.

Two engines, one guarantee:

    engine="llm"        Groq function-calling. The model chooses the tools.
    engine="scripted"   A deterministic walk of the blueprint. No LLM at all.

Whichever engine runs, `AgentGuard` sits between the chosen action and its
execution. The guard — not the model — is the thing that upholds the risk tier.
That is the point: autonomy on top, a hard fence underneath.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from app.agent import tools
from app.config import Settings
from app.constants import RiskDecision

logger = logging.getLogger(__name__)

MAX_STEPS = 12  # A hard ceiling so a looping model can never run unbounded.


class RunStatus(str, Enum):
    COMPLETED = "COMPLETED"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    REFUSED = "REFUSED"
    FAILED = "FAILED"
    MAX_STEPS_REACHED = "MAX_STEPS_REACHED"


class StepType(str, Enum):
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    BLOCKED = "blocked"
    FINAL = "final"


class TraceStep(BaseModel):
    seq: int
    type: StepType
    tool: Optional[str] = None
    args: Optional[dict] = None
    content: str
    blocked: bool = False


class AgentRunResult(BaseModel):
    process_id: str
    process_name: str
    risk_decision: RiskDecision
    engine: str
    status: RunStatus
    summary: str
    trace: list[TraceStep]

    @property
    def actions_taken(self) -> int:
        return sum(
            1
            for s in self.trace
            if s.type == StepType.TOOL_CALL
            and s.tool in tools.CONSEQUENTIAL_TOOLS
            and not s.blocked
        )


# ---------------------------------------------------------------------------
# The gate, at execution time.
# ---------------------------------------------------------------------------

@dataclass
class AgentGuard:
    """Decides, per tool call, whether the action may proceed.

    Enforced in Python. The model's intent is an input to this decision, never
    an override of it — exactly like harden_with_policy in the discovery
    pipeline, but for actions instead of labels.
    """

    risk_decision: RiskDecision
    _approval_pending: bool = field(default=False, init=False)

    def may_start(self) -> tuple[bool, str]:
        if self.risk_decision == RiskDecision.TOO_RISKY:
            return False, (
                "Refused: this process is classified TOO_RISKY. No autonomous "
                "action is permitted; a human must handle it end to end."
            )
        return True, ""

    def check(self, tool_name: str) -> tuple[bool, str]:
        """Return (allowed, reason_if_blocked) for a proposed tool call."""
        # Reads and low-consequence side effects are always fine.
        if tool_name not in tools.CONSEQUENTIAL_TOOLS:
            return True, ""

        # A consequential write.
        if self.risk_decision == RiskDecision.PRE_APPROVED:
            return True, ""

        if self.risk_decision == RiskDecision.HUMAN_IN_THE_LOOP:
            self._approval_pending = True
            return False, (
                "Blocked by governance: a Human-in-the-Loop process cannot apply "
                "a change without human authorisation. The agent must request "
                "approval and stop here."
            )

        # TOO_RISKY should never reach a tool call (may_start refuses first),
        # but defend in depth.
        return False, "Blocked: TOO_RISKY processes may take no action."

    @property
    def approval_pending(self) -> bool:
        return self._approval_pending


# ---------------------------------------------------------------------------
# Shared helpers.
# ---------------------------------------------------------------------------

def _goal_prompt(process_name: str, blueprint: dict, risk_decision: RiskDecision) -> str:
    steps = blueprint.get("steps", [])
    step_lines = "\n".join(
        f"  {i + 1}. {s.get('name', '?')} — {s.get('description', '')}"
        f"{' [REQUIRES HUMAN APPROVAL]' if s.get('requires_approval') else ''}"
        for i, s in enumerate(steps)
    ) or "  (no explicit steps; use your judgement)"

    governance = {
        RiskDecision.PRE_APPROVED: (
            "This process is PRE_APPROVED. You may complete every step "
            "autonomously, including applying updates."
        ),
        RiskDecision.HUMAN_IN_THE_LOOP: (
            "This process is HUMAN_IN_THE_LOOP. Do the safe preparatory work "
            "yourself (fetch, validate, notify), but you MUST call "
            "request_human_approval instead of apply_update for any step that "
            "changes a system. Do not attempt to apply changes yourself."
        ),
    }.get(risk_decision, "")

    return (
        f"You are an automation agent executing the process '{process_name}'.\n"
        f"Trigger: {blueprint.get('trigger', 'n/a')}\n\n"
        f"Blueprint steps:\n{step_lines}\n\n"
        f"GOVERNANCE: {governance}\n\n"
        "Work step by step. Call one tool at a time, read its result, then "
        "decide the next action. When the work is done, call complete_task."
    )


# ---------------------------------------------------------------------------
# Engine 1 — deterministic scripted walk (no LLM). Reliable for demos.
# ---------------------------------------------------------------------------

def run_scripted(
    process_name: str,
    blueprint: dict,
    guard: AgentGuard,
) -> tuple[RunStatus, str, list[TraceStep]]:
    trace: list[TraceStep] = []
    seq = 0

    def add(step_type: StepType, content: str, tool: str | None = None,
            args: dict | None = None, blocked: bool = False) -> None:
        nonlocal seq
        seq += 1
        trace.append(TraceStep(seq=seq, type=step_type, tool=tool, args=args,
                               content=content, blocked=blocked))

    add(StepType.PLAN, f"Planning execution of '{process_name}' across "
        f"{len(blueprint.get('steps', []))} step(s).")

    for step in blueprint.get("steps", []):
        name = step.get("name", "step")
        system = step.get("system", "system")
        needs_approval = bool(step.get("requires_approval"))

        # Always safe: read + validate.
        for tool_name, args in (
            ("fetch_record", {"record_ref": name}),
            ("validate_fields", {"fields": name}),
        ):
            add(StepType.TOOL_CALL, f"Calling {tool_name} for '{name}'.",
                tool=tool_name, args=args)
            result = tools.execute_tool(tool_name, args)
            add(StepType.OBSERVATION, json.dumps(result), tool=tool_name)

        # The consequential move: apply_update — subject to the guard.
        allowed, reason = guard.check("apply_update")
        write_args = {"system": system, "change": f"complete '{name}'"}
        if allowed:
            add(StepType.TOOL_CALL, f"Applying update in {system} for '{name}'.",
                tool="apply_update", args=write_args)
            result = tools.execute_tool("apply_update", write_args)
            add(StepType.OBSERVATION, json.dumps(result), tool="apply_update")
        else:
            add(StepType.BLOCKED, reason, tool="apply_update", args=write_args,
                blocked=True)
            # The agent does the right thing: asks a human, then stops.
            appr = {"reason": step.get("approval_condition") or
                    f"human authorisation required for '{name}'"}
            add(StepType.TOOL_CALL, "Requesting human approval.",
                tool="request_human_approval", args=appr)
            result = tools.execute_tool("request_human_approval", appr)
            add(StepType.OBSERVATION, json.dumps(result),
                tool="request_human_approval")
            summary = (f"Paused at '{name}': prep done autonomously, "
                       "awaiting human approval before the consequential change.")
            add(StepType.FINAL, summary)
            return RunStatus.AWAITING_HUMAN_APPROVAL, summary, trace

    summary = (f"Completed '{process_name}' autonomously — "
               f"{guard.risk_decision.value} process, no human needed.")
    add(StepType.TOOL_CALL, "Marking task complete.", tool="complete_task",
        args={"summary": summary})
    add(StepType.FINAL, summary)
    return RunStatus.COMPLETED, summary, trace


# ---------------------------------------------------------------------------
# Engine 2 — Groq function-calling. The model drives.
# ---------------------------------------------------------------------------

async def run_llm(
    process_name: str,
    blueprint: dict,
    guard: AgentGuard,
    settings: Settings,
    timeout: float = 30.0,
) -> tuple[RunStatus, str, list[TraceStep]]:
    trace: list[TraceStep] = []
    seq = 0

    def add(step_type: StepType, content: str, tool: str | None = None,
            args: dict | None = None, blocked: bool = False) -> None:
        nonlocal seq
        seq += 1
        trace.append(TraceStep(seq=seq, type=step_type, tool=tool, args=args,
                               content=content, blocked=blocked))

    system_prompt = (
        "You are a careful automation agent. You accomplish a business process "
        "by calling tools one at a time. You never claim to have done something "
        "you did not do via a tool. You respect governance: if a change needs "
        "human approval, you request it rather than applying it yourself."
    )
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": _goal_prompt(process_name, blueprint,
                                                  guard.risk_decision)},
    ]

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    url = settings.LLM_API_URL or tools_endpoint()

    for _ in range(MAX_STEPS):
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": messages,
            "tools": tools.TOOL_SCHEMAS,
            "tool_choice": "auto",
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=headers, json=payload,
                                         timeout=timeout)
                resp.raise_for_status()
                message = resp.json()["choices"][0]["message"]
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            logger.warning("Agent LLM call failed for %r: %s", process_name, exc)
            summary = f"Agent run failed to reach the model: {exc}"
            add(StepType.FINAL, summary)
            return RunStatus.FAILED, summary, trace

        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            # The model answered in prose — treat as the final word.
            summary = (message.get("content") or "").strip() or "Run finished."
            add(StepType.FINAL, summary)
            return RunStatus.COMPLETED, summary, trace

        # Record the model's own reasoning, if it narrated any.
        if message.get("content"):
            add(StepType.PLAN, message["content"].strip())

        # Keep the assistant turn in the conversation so tool results attach.
        messages.append({
            "role": "assistant",
            "content": message.get("content") or "",
            "tool_calls": tool_calls,
        })

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}

            # --- the gate --------------------------------------------------
            allowed, reason = guard.check(name)
            if not allowed:
                add(StepType.BLOCKED, reason, tool=name, args=args, blocked=True)
                # Tell the model why, so it self-corrects toward asking a human.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": json.dumps({"ok": False, "blocked": True,
                                           "reason": reason}),
                })
                continue

            add(StepType.TOOL_CALL, f"Calling {name}.", tool=name, args=args)
            result = tools.execute_tool(name, args)
            add(StepType.OBSERVATION, json.dumps(result), tool=name)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": json.dumps(result),
            })

            # Terminal tools end the run.
            if name == "complete_task":
                summary = args.get("summary") or "Task complete."
                add(StepType.FINAL, summary)
                return RunStatus.COMPLETED, summary, trace
            if name == "request_human_approval":
                summary = (f"Paused: agent requested human approval — "
                           f"{args.get('reason', 'authorisation required')}.")
                add(StepType.FINAL, summary)
                return RunStatus.AWAITING_HUMAN_APPROVAL, summary, trace

    summary = "Reached the step ceiling without completing. Halted for safety."
    add(StepType.FINAL, summary)
    return RunStatus.MAX_STEPS_REACHED, summary, trace


def tools_endpoint() -> str:
    return "https://api.groq.com/openai/v1/chat/completions"


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------

async def run_agent(
    *,
    process_id: str,
    process_name: str,
    risk_decision: RiskDecision,
    blueprint: dict,
    settings: Settings,
    engine: str = "auto",
) -> AgentRunResult:
    """Execute a process with the agent, under the risk gate.

    engine: "auto" uses the LLM when a key is present, else the scripted walk;
    "llm" forces Groq; "scripted" forces the deterministic engine.
    """
    guard = AgentGuard(risk_decision=risk_decision)

    ok, refusal = guard.may_start()
    if not ok:
        trace = [TraceStep(seq=1, type=StepType.FINAL, content=refusal,
                           blocked=True)]
        return AgentRunResult(
            process_id=process_id, process_name=process_name,
            risk_decision=risk_decision, engine="gate",
            status=RunStatus.REFUSED, summary=refusal, trace=trace,
        )

    use_llm = engine == "llm" or (engine == "auto" and bool(settings.GROQ_API_KEY))

    if use_llm:
        status, summary, trace = await run_llm(process_name, blueprint, guard,
                                               settings)
        engine_used = "llm"
    else:
        status, summary, trace = run_scripted(process_name, blueprint, guard)
        engine_used = "scripted"

    return AgentRunResult(
        process_id=process_id, process_name=process_name,
        risk_decision=risk_decision, engine=engine_used,
        status=status, summary=summary, trace=trace,
    )
