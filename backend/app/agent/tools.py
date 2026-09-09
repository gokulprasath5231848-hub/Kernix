"""The agent's toolbox.

Every tool here is a STUB: it returns a plausible, deterministic result and
touches no real system. That is deliberate for a demo — the agent's *reasoning*,
*tool selection* and *governance* are real, while the endpoints are mocked so a
run can never cause real-world damage on stage.

Tools are split by consequence:

    READ / COMPUTE tools  (fetch_record, validate_fields)
        No side effects. Always allowed, at any risk tier.

    ACTION tools          (apply_update, send_notification)
        Change the world. Subject to the execution-time risk gate in
        executor.py. apply_update is the consequential write; the gate can block
        it regardless of what the model decided.

    CONTROL tools         (request_human_approval, complete_task)
        The agent's way of yielding control — either to a human, or by declaring
        the job finished.

Each tool exposes an OpenAI-compatible JSON schema (Groq speaks the same
dialect) so the model can call them, plus a pure Python executor used by both
the LLM loop and the deterministic fallback.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Tool classification. The executor consults these sets; it never trusts the
# model to tell it whether a tool is consequential.
# ---------------------------------------------------------------------------

READ_TOOLS = {"fetch_record", "validate_fields"}
ACTION_TOOLS = {"apply_update", "send_notification"}
CONTROL_TOOLS = {"request_human_approval", "complete_task"}

# The single consequential write. This is the tool the risk gate guards.
CONSEQUENTIAL_TOOLS = {"apply_update"}


def _fake_id(seed: str) -> str:
    """A stable pseudo-id so repeated demos produce the same-looking output."""
    return hashlib.sha1(seed.encode()).hexdigest()[:8].upper()


# ---------------------------------------------------------------------------
# Executors — pure functions, no I/O. Return a JSON-serialisable dict.
# ---------------------------------------------------------------------------

def _fetch_record(record_ref: str = "", **_: Any) -> dict:
    ref = record_ref or "record"
    return {
        "ok": True,
        "record_id": _fake_id(ref),
        "reference": ref,
        "fields": {"amount": 1240.00, "currency": "USD", "status": "open"},
        "note": "(stubbed read — no real system was queried)",
    }


def _validate_fields(fields: str = "", **_: Any) -> dict:
    # A read-only check. Deterministically "passes" so the demo flows; a real
    # implementation would apply the process's business rules here.
    return {
        "ok": True,
        "valid": True,
        "checked": fields or "all fields",
        "issues": [],
    }


def _apply_update(system: str = "", change: str = "", **_: Any) -> dict:
    return {
        "ok": True,
        "system": system or "target system",
        "change": change or "update applied",
        "confirmation": _fake_id(f"{system}:{change}"),
        "note": "(stubbed write — no real system was modified)",
    }


def _send_notification(channel: str = "", message: str = "", **_: Any) -> dict:
    return {
        "ok": True,
        "channel": channel or "ops-inbox",
        "delivered": True,
        "message": message,
        "note": "(stubbed notification — nothing was actually sent)",
    }


def _request_human_approval(reason: str = "", **_: Any) -> dict:
    # The agent declaring it has reached a decision only a human may make. The
    # executor treats this as a pause; the human is NOT auto-approved here.
    return {
        "ok": True,
        "approval_requested": True,
        "granted": False,
        "reason": reason or "human authorisation required",
        "status": "awaiting_human_approval",
    }


def _complete_task(summary: str = "", **_: Any) -> dict:
    return {"ok": True, "completed": True, "summary": summary or "task complete"}


EXECUTORS: dict[str, Callable[..., dict]] = {
    "fetch_record": _fetch_record,
    "validate_fields": _validate_fields,
    "apply_update": _apply_update,
    "send_notification": _send_notification,
    "request_human_approval": _request_human_approval,
    "complete_task": _complete_task,
}


def execute_tool(name: str, arguments: dict) -> dict:
    """Run a stub tool. Unknown tools return a structured error rather than
    raising, so a hallucinated tool name can't crash a run."""
    fn = EXECUTORS.get(name)
    if fn is None:
        return {"ok": False, "error": f"unknown tool '{name}'"}
    try:
        return fn(**(arguments or {}))
    except TypeError as exc:
        # Model supplied unexpected argument names — degrade, don't crash.
        return {"ok": False, "error": f"bad arguments for '{name}': {exc}"}


# ---------------------------------------------------------------------------
# OpenAI/Groq function-calling schemas.
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "fetch_record",
            "description": "Read a record from a source system. No side effects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "record_ref": {
                        "type": "string",
                        "description": "Which record/case to read.",
                    }
                },
                "required": ["record_ref"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_fields",
            "description": "Check that data satisfies the process rules. No side effects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fields": {
                        "type": "string",
                        "description": "The fields or data being validated.",
                    }
                },
                "required": ["fields"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_update",
            "description": (
                "Write a change to a source system. This is a CONSEQUENTIAL "
                "action and may be blocked by governance depending on the "
                "process's risk tier."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "system": {"type": "string", "description": "System to update."},
                    "change": {"type": "string", "description": "The change to apply."},
                },
                "required": ["system", "change"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Notify a person or channel of progress. Low-consequence side effect.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["channel", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_human_approval",
            "description": (
                "Hand control to a human before a step that needs authorisation. "
                "Use this instead of apply_update whenever a step requires approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why a human decision is needed here.",
                    }
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Declare the automation finished. Call this last.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "One-line summary of what was accomplished.",
                    }
                },
                "required": ["summary"],
            },
        },
    },
]
