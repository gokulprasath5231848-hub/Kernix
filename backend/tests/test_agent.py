"""Agent execution tests.

The invariant under test is the same one the whole product is built around,
now at the moment of *action* rather than classification:

    the score can never buy an agent permission the risk gate withheld.

These run entirely on the deterministic ('scripted') engine — no network, no
API key — so the guarantee is proven without depending on an LLM.
"""
import pytest

from app.agent.executor import (
    AgentGuard,
    RunStatus,
    StepType,
    run_agent,
)
from app.agent import tools
from app.config import get_settings
from app.constants import RiskDecision

# asyncio_mode = "auto" (pyproject) marks the async tests automatically; the
# synchronous guard tests below must stay unmarked, so no module-level mark here.


def _blueprint(requires_approval: bool):
    return {
        "trigger": "test",
        "estimated_savings_hours": 1.0,
        "steps": [
            {"name": "Read data", "description": "d", "system": "SAP",
             "requires_approval": False},
            {"name": "Post change", "description": "d", "system": "SAP",
             "requires_approval": requires_approval,
             "approval_condition": "needs a human"},
        ],
    }


async def _run(risk: RiskDecision, requires_approval: bool):
    return await run_agent(
        process_id="p1",
        process_name="Test Process",
        risk_decision=risk,
        blueprint=_blueprint(requires_approval),
        settings=get_settings(),
        engine="scripted",
    )


# --- the guard, in isolation -------------------------------------------------

def test_guard_refuses_to_start_too_risky():
    ok, reason = AgentGuard(RiskDecision.TOO_RISKY).may_start()
    assert ok is False
    assert "TOO_RISKY" in reason


def test_guard_allows_reads_at_every_tier():
    for tier in RiskDecision:
        guard = AgentGuard(tier)
        for tool in tools.READ_TOOLS:
            allowed, _ = guard.check(tool)
            assert allowed, f"{tool} should be allowed for {tier}"


def test_guard_blocks_write_for_hitl_but_allows_for_preapproved():
    assert AgentGuard(RiskDecision.PRE_APPROVED).check("apply_update")[0] is True
    assert AgentGuard(RiskDecision.HUMAN_IN_THE_LOOP).check("apply_update")[0] is False


# --- full runs, per risk tier ------------------------------------------------

async def test_preapproved_runs_to_completion_and_acts():
    result = await _run(RiskDecision.PRE_APPROVED, requires_approval=False)
    assert result.status == RunStatus.COMPLETED
    assert result.engine == "scripted"
    # It actually performed consequential writes — it did not just plan.
    assert result.actions_taken >= 1
    assert not any(s.blocked for s in result.trace)


async def test_hitl_pauses_and_never_writes():
    result = await _run(RiskDecision.HUMAN_IN_THE_LOOP, requires_approval=True)
    assert result.status == RunStatus.AWAITING_HUMAN_APPROVAL
    # The consequential write was blocked, so zero real actions were taken.
    assert result.actions_taken == 0
    assert any(s.blocked and s.tool == "apply_update" for s in result.trace)
    # And it did the right thing: asked a human.
    assert any(s.tool == "request_human_approval" for s in result.trace)


async def test_too_risky_is_refused_before_any_step():
    result = await _run(RiskDecision.TOO_RISKY, requires_approval=True)
    assert result.status == RunStatus.REFUSED
    assert result.actions_taken == 0
    # A refusal is a single, explicit terminal step — not a silent no-op.
    assert len(result.trace) == 1
    assert result.trace[0].type == StepType.FINAL
    assert result.trace[0].blocked is True


# --- the same guarantee across the HTTP boundary -----------------------------

async def test_agent_endpoint_preapproved(client):
    r = await client.post(f"/api/processes/{client.ids['safe']}/agent/run")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == RunStatus.COMPLETED.value
    assert body["risk_decision"] == RiskDecision.PRE_APPROVED.value


async def test_agent_endpoint_hitl_pauses(client):
    r = await client.post(f"/api/processes/{client.ids['hitl']}/agent/run")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == RunStatus.AWAITING_HUMAN_APPROVAL.value


async def test_agent_endpoint_too_risky_refused(client):
    r = await client.post(f"/api/processes/{client.ids['risky']}/agent/run")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == RunStatus.REFUSED.value
    # The highest-scoring process in the catalog is the one the agent refuses.
    assert body["risk_decision"] == RiskDecision.TOO_RISKY.value


async def test_agent_run_is_audited(client):
    await client.post(f"/api/processes/{client.ids['safe']}/agent/run")
    r = await client.get("/api/audit")
    actions = [row["action"] for row in r.json()]
    assert any(a.startswith("AGENT_") for a in actions)


# --- the LLM engine, with the model mocked -----------------------------------
#
# Proves the Groq tool-calling loop parses tool_calls, runs them through the
# SAME guard, and terminates — without a live API key. A tiny fake stands in for
# httpx so no network is touched.

class _FakeResponse:
    def __init__(self, message):
        self._message = message

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": self._message}]}


class _FakeAsyncClient:
    """Returns a scripted sequence of assistant turns, one per POST."""

    _turns: list = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, *a, **k):
        message = _FakeAsyncClient._turns.pop(0)
        return _FakeResponse(message)


def _tool_call(name, args):
    import json
    return {"id": f"call_{name}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


async def test_llm_engine_preapproved_completes(monkeypatch):
    """Model applies an update then completes — guard lets it through."""
    _FakeAsyncClient._turns = [
        {"content": "I'll update the record.", "tool_calls": [
            _tool_call("apply_update", {"system": "SAP", "change": "post"})]},
        {"content": "Done.", "tool_calls": [
            _tool_call("complete_task", {"summary": "All steps applied."})]},
    ]
    monkeypatch.setattr("app.agent.executor.httpx.AsyncClient", _FakeAsyncClient)

    settings = get_settings()
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key", raising=False)

    result = await run_agent(
        process_id="p1", process_name="Test", risk_decision=RiskDecision.PRE_APPROVED,
        blueprint=_blueprint(False), settings=settings, engine="llm",
    )
    assert result.engine == "llm"
    assert result.status == RunStatus.COMPLETED
    assert result.actions_taken == 1


async def test_llm_engine_hitl_write_is_blocked(monkeypatch):
    """Model tries to apply a change on a HITL process; the guard blocks it and
    the model is nudged to request approval instead."""
    _FakeAsyncClient._turns = [
        {"content": "Applying the change.", "tool_calls": [
            _tool_call("apply_update", {"system": "SAP", "change": "post"})]},
        {"content": "I need sign-off.", "tool_calls": [
            _tool_call("request_human_approval", {"reason": "needs a human"})]},
    ]
    monkeypatch.setattr("app.agent.executor.httpx.AsyncClient", _FakeAsyncClient)

    settings = get_settings()
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key", raising=False)

    result = await run_agent(
        process_id="p1", process_name="Test",
        risk_decision=RiskDecision.HUMAN_IN_THE_LOOP,
        blueprint=_blueprint(True), settings=settings, engine="llm",
    )
    assert result.status == RunStatus.AWAITING_HUMAN_APPROVAL
    # The write never happened, even though the model asked for it.
    assert result.actions_taken == 0
    assert any(s.blocked and s.tool == "apply_update" for s in result.trace)
