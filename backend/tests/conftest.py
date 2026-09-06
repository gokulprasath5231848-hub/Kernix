"""Test fixtures.

Integration tests run against a real (SQLite in-memory) database rather than
mocks, so the ORM mappings, relationships and query logic are genuinely
exercised. The models use dialect-portable column types for this reason.
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db_session
from app.main import app
from app.models import AuditLog, Blueprint, Event, Process, Score, ScoringWeights
from app.constants import SCORING_WEIGHTS, RiskDecision
from app.scoring.risk_gate import evaluate_risk


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield maker
    await engine.dispose()


def _make_process(name, *, sensitive, rule_based, value_score, weights_id):
    """Build a process + score whose risk decision is DERIVED, never asserted."""
    decision, reason = evaluate_risk(
        sensitive_outcome=sensitive, fully_rule_based=rule_based
    )
    process = Process(
        id=uuid.uuid4(),
        name=name,
        department="Finance",
        cases_per_month=100,
        steps=5,
        systems_touched=2,
        systems=["SAP", "Workday"],
    )
    score = Score(
        process_id=process.id,
        frequency_volume=90, manual_time=90, rule_determinism=90,
        api_readiness=90, exception_frequency=90, privacy_risk=90,
        value_score=value_score,
        sensitive_outcome=sensitive,
        fully_rule_based=rule_based,
        risk_decision=decision.value,
        reason=reason,
        weights_id=weights_id,
    )
    return process, score


@pytest_asyncio.fixture
async def seeded(session_factory):
    """Three processes covering every risk class, including the critical
    high-score-but-blocked case."""
    async with session_factory() as s:
        weights = ScoringWeights(weights=SCORING_WEIGHTS)
        s.add(weights)
        await s.flush()

        safe, safe_score = _make_process(
            "Expense Reconciliation & Audit",
            sensitive=False, rule_based=True, value_score=92.0, weights_id=weights.id,
        )
        hitl, hitl_score = _make_process(
            "Vendor Onboarding Compliance",
            sensitive=False, rule_based=False, value_score=78.0, weights_id=weights.id,
        )
        # The trust-building row: highest score in the catalog, still blocked.
        risky, risky_score = _make_process(
            "Payroll Tax Remittance & Filing",
            sensitive=True, rule_based=True, value_score=97.0, weights_id=weights.id,
        )

        s.add_all([safe, hitl, risky, safe_score, hitl_score, risky_score])
        await s.flush()

        # Evidence belongs to the safe process only — used to prove the
        # evidence trail is scoped, not a global sample.
        s.add_all([
            Event(
                process_id=safe.id, case_id="ev_1",
                activity_raw="Coupa invoice parsed", activity_normalised="coupa invoice parsed",
                event_time=__import__("datetime").datetime(2025, 2, 24, 10, 14),
                actor_masked="sys_worker_4", system="Coupa", confidence=1.0,
            ),
            Event(
                process_id=hitl.id, case_id="ev_2",
                activity_raw="Vendor doc received", activity_normalised="vendor doc received",
                event_time=__import__("datetime").datetime(2025, 2, 24, 11, 0),
                actor_masked="sys_worker_2", system="DocuSign", confidence=1.0,
            ),
        ])
        s.add(Blueprint(
            process_id=safe.id,
            steps=[{"name": "Verify", "description": "d", "system": "SAP", "requires_approval": False}],
            trigger="Webhook",
            estimated_savings_hours=7.5,
        ))
        s.add(Blueprint(
            process_id=risky.id,
            steps=[{"name": "File", "description": "d", "system": "IRS", "requires_approval": True}],
            trigger="Schedule",
            estimated_savings_hours=40.0,
        ))
        await s.commit()

        return {"safe": safe.id, "hitl": hitl.id, "risky": risky.id}


@pytest_asyncio.fixture
async def client(session_factory, seeded):
    async def _override():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.ids = seeded  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()
