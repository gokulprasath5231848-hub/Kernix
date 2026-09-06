"""API integration tests.

The most important cases here are the ones that prove the risk gate holds
across the HTTP boundary — not just inside the scoring module.
"""
import pytest

from app.constants import RiskDecision

pytestmark = pytest.mark.asyncio


async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_list_processes_returns_all(client):
    r = await client.get("/api/processes")
    assert r.status_code == 200
    body = r.json()
    assert body["total_count"] == 3
    assert len(body["items"]) == 3


async def test_list_is_sorted_by_score_descending(client):
    r = await client.get("/api/processes")
    scores = [p["score"]["value_score"] for p in r.json()["items"]]
    assert scores == sorted(scores, reverse=True)
    # The 97-scoring process ranks first even though it is blocked.
    assert scores[0] == 97.0


async def test_filter_by_risk_class(client):
    r = await client.get(f"/api/processes?risk_class={RiskDecision.TOO_RISKY.value}")
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Payroll Tax Remittance & Filing"


# --- The invariant, enforced across the HTTP boundary ------------------------

async def test_highest_scoring_process_is_still_blocked(client):
    """97/100 and sensitive → still TOO_RISKY. Score never overrides the gate."""
    r = await client.get(f"/api/processes/{client.ids['risky']}")
    body = r.json()
    assert body["score"]["value_score"] == 97.0
    assert body["score"]["risk_decision"] == RiskDecision.TOO_RISKY.value


async def test_blueprint_forbidden_for_too_risky(client):
    """403, not 404 — the refusal is explicit, not an accidental empty result."""
    r = await client.get(f"/api/processes/{client.ids['risky']}/blueprint")
    assert r.status_code == 403
    assert "TOO_RISKY" in r.json()["detail"]


async def test_blueprint_allowed_for_safe_process(client):
    r = await client.get(f"/api/processes/{client.ids['safe']}/blueprint")
    assert r.status_code == 200
    assert r.json()["trigger"] == "Webhook"


async def test_cannot_queue_too_risky_for_approval(client):
    r = await client.post(
        f"/api/processes/{client.ids['risky']}/blueprint/submit-for-approval"
    )
    assert r.status_code == 403


async def test_safe_process_can_be_queued_for_approval(client):
    r = await client.post(
        f"/api/processes/{client.ids['safe']}/blueprint/submit-for-approval"
    )
    assert r.status_code == 200
    # Queued for a human — never auto-executed.
    assert r.json()["status"] == "awaiting_human_approval"


# --- Evidence trail provenance ----------------------------------------------

async def test_evidence_trail_is_scoped_to_its_process(client):
    """Regression test: the trail must not return events from other processes."""
    r = await client.get(f"/api/processes/{client.ids['safe']}")
    trail = r.json()["evidence_trail"]
    assert len(trail) == 1
    assert trail[0]["case_id"] == "ev_1"

    r2 = await client.get(f"/api/processes/{client.ids['hitl']}")
    trail2 = r2.json()["evidence_trail"]
    assert len(trail2) == 1
    assert trail2[0]["case_id"] == "ev_2"


async def test_process_with_no_events_has_empty_trail(client):
    r = await client.get(f"/api/processes/{client.ids['risky']}")
    assert r.json()["evidence_trail"] == []


# --- Re-evaluation -----------------------------------------------------------

async def test_reevaluate_recomputes_and_preserves_risk(client):
    r = await client.post(f"/api/processes/{client.ids['risky']}/reevaluate")
    assert r.status_code == 200
    body = r.json()
    # Re-scoring must never quietly unblock a sensitive process.
    assert body["risk_decision"] == RiskDecision.TOO_RISKY.value


async def test_unknown_process_returns_404(client):
    r = await client.get("/api/processes/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
