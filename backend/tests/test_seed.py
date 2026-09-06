"""Seed data integrity tests.

The demo catalog is what reviewers actually click through, so its shape is a
contract — not incidental. These tests fail loudly if the seed drifts away from
the documented 48-process / 28-14-6 catalog, or if any seeded row ever displays
a risk classification the real gate would not produce.
"""
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import RiskDecision
from app.models import Blueprint, Event, Process, Score
from app.scoring.risk_gate import evaluate_risk
from app.seed import seed_database

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seeded_db(session_factory):
    async with session_factory() as session:
        await seed_database(session)
    return session_factory


async def _all_scores(factory) -> list[Score]:
    async with factory() as s:
        return list((await s.execute(select(Score))).scalars().all())


async def test_catalog_has_48_processes(seeded_db):
    async with seeded_db() as s:
        count = await s.scalar(select(func.count(Process.id)))
    assert count == 48


async def test_risk_distribution_matches_documented_28_14_6(seeded_db):
    scores = await _all_scores(seeded_db)
    counts = {rc: 0 for rc in RiskDecision}
    for sc in scores:
        counts[RiskDecision(sc.risk_decision)] += 1

    assert counts[RiskDecision.PRE_APPROVED] == 28
    assert counts[RiskDecision.HUMAN_IN_THE_LOOP] == 14
    assert counts[RiskDecision.TOO_RISKY] == 6


async def test_no_seeded_row_contradicts_the_risk_gate(seeded_db):
    """Every stored classification must be reproducible from the gate alone."""
    scores = await _all_scores(seeded_db)
    for sc in scores:
        expected, _ = evaluate_risk(
            sensitive_outcome=sc.sensitive_outcome,
            fully_rule_based=sc.fully_rule_based,
        )
        assert sc.risk_decision == expected.value, (
            f"Seeded score {sc.id} stores {sc.risk_decision} but the gate "
            f"produces {expected.value}"
        )


async def test_highest_scoring_process_is_blocked(seeded_db):
    """The trust-building row: top of the catalog by score, still gated."""
    scores = await _all_scores(seeded_db)
    top = max(scores, key=lambda s: s.value_score)
    assert top.value_score == 97.0
    assert top.risk_decision == RiskDecision.TOO_RISKY.value
    assert top.sensitive_outcome is True


async def test_every_score_has_an_explanation(seeded_db):
    """A score with no reason is not auditable."""
    scores = await _all_scores(seeded_db)
    assert all(s.reason for s in scores)


async def test_every_score_references_its_weights_version(seeded_db):
    """Scores must stay explainable after weights change."""
    scores = await _all_scores(seeded_db)
    assert all(s.weights_id is not None for s in scores)


async def test_seeded_events_are_attached_to_a_process(seeded_db):
    """Orphan events would make the evidence trail unattributable."""
    async with seeded_db() as s:
        events = list((await s.execute(select(Event))).scalars().all())
    assert events
    assert all(e.process_id is not None for e in events)


async def test_seeded_blueprint_contains_a_human_gate(seeded_db):
    async with seeded_db() as s:
        blueprints = list((await s.execute(select(Blueprint))).scalars().all())
    assert blueprints
    for bp in blueprints:
        assert any(step.get("requires_approval") for step in bp.steps)


async def test_seeding_is_idempotent(seeded_db):
    """Restarting the API must not duplicate the catalog."""
    async with seeded_db() as s:
        await seed_database(s)
    async with seeded_db() as s:
        count = await s.scalar(select(func.count(Process.id)))
    assert count == 48
