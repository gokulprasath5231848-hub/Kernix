"""Tests for the end-to-end discovery pipeline.

The most important tests here are the ones proving that the semantic layer
cannot make a process look safer than deterministic policy says it is. That
property is what makes it safe to put an LLM upstream of the risk gate.
"""
import datetime as dt
import uuid

import pytest
from sqlalchemy import select

from app.config import Settings
from app.constants import RiskDecision
from app.ingestion.parser import parse_csv, parse_timestamp
from app.models import Event, Process, Score
from app.pipeline.metrics import compute_process_metrics
from app.pipeline.orchestrator import run_discovery
from app.pipeline.semantic import (
    SemanticAnalysis,
    apply_policy,
    harden_with_policy,
)

NO_LLM = Settings(GROQ_API_KEY="")


# --------------------------------------------------------------------------
# The core guarantee: the model can escalate risk, never reduce it.
# --------------------------------------------------------------------------

def test_policy_escalates_when_model_says_process_is_safe():
    """A model that wrongly declares payroll filing safe must be overruled."""
    wrong = SemanticAnalysis(
        canonical_process_name="Payroll Tax Remittance and Filing",
        sensitive_outcome=False,      # model is wrong
        rule_based=True,
        human_judgment_required=False,
        determinism_score=99.0,
    )
    hardened = harden_with_policy(wrong, ["payroll tax remittance and filing"])
    assert hardened.sensitive_outcome is True
    assert hardened.automation_candidate is False


def test_model_can_still_escalate_beyond_policy():
    """If policy sees nothing but the model does, the model's caution wins."""
    cautious = SemanticAnalysis(
        canonical_process_name="Adjust Customer Balance",
        sensitive_outcome=True,       # model is more careful than policy
        rule_based=False,
    )
    hardened = harden_with_policy(cautious, ["adjust customer balance"])
    assert hardened.sensitive_outcome is True


def test_model_cannot_mark_judgement_work_as_rule_based():
    analysis = SemanticAnalysis(
        canonical_process_name="Review Vendor Compliance",
        sensitive_outcome=False,
        rule_based=True,              # model is wrong; "review" implies judgement
        human_judgment_required=False,
    )
    hardened = harden_with_policy(analysis, ["review vendor onboarding documents"])
    assert hardened.rule_based is False
    assert hardened.human_judgment_required is True


def test_genuinely_safe_process_is_left_alone():
    """Hardening must not make everything risky — that would be useless."""
    analysis = SemanticAnalysis(
        canonical_process_name="Match Line Items",
        sensitive_outcome=False,
        rule_based=True,
        human_judgment_required=False,
        determinism_score=95.0,
    )
    hardened = harden_with_policy(analysis, ["match line items", "record result"])
    assert hardened.sensitive_outcome is False
    assert hardened.rule_based is True


@pytest.mark.parametrize(
    "text",
    ["payroll tax filing", "employee termination letter", "wire transfer approval",
     "patient diagnosis review", "loan approval decision"],
)
def test_sensitive_domains_are_detected_by_policy(text):
    assert apply_policy([text]).sensitive is True


def test_ordinary_work_is_not_flagged_sensitive():
    assert apply_policy(["match line items", "send confirmation email"]).sensitive is False


# --------------------------------------------------------------------------
# Metrics are measured, not invented
# --------------------------------------------------------------------------

def _ev(case, activity, minutes, system="SAP"):
    return Event(
        id=uuid.uuid4(), case_id=case, activity_raw=activity,
        activity_normalised=activity.lower(),
        event_time=dt.datetime(2025, 3, 1, tzinfo=dt.timezone.utc) + dt.timedelta(minutes=minutes),
        actor_masked="[EMAIL]", system=system, confidence=1.0,
    )


def test_metrics_measure_real_handling_time():
    events = [_ev("c1", "start", 0), _ev("c1", "finish", 30),
              _ev("c2", "start", 60), _ev("c2", "finish", 80)]
    m = compute_process_metrics(events)
    assert m.case_count == 2
    assert m.avg_minutes_per_case == pytest.approx(25.0)


def test_rework_is_detected_and_inverted_in_the_score():
    clean = compute_process_metrics([_ev("c1", "submit", 0), _ev("c1", "approve", 5)])
    messy = compute_process_metrics([_ev("c2", "submit", 0), _ev("c2", "correct error", 5)])
    assert messy.rework_rate > clean.rework_rate
    # Fewer exceptions must score HIGHER, not lower.
    assert messy.factors["exception_frequency"] < clean.factors["exception_frequency"]


def test_metrics_handle_empty_input():
    m = compute_process_metrics([])
    assert m.case_count == 0
    assert set(m.factors) == {
        "frequency_volume", "manual_time", "rule_determinism",
        "api_readiness", "exception_frequency", "privacy_risk",
    }


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "2025-03-01T09:00:00", "2025-03-01 09:00:00", "2025-03-01",
    "01/03/2025 09:00", "2025-03-01T09:00:00Z",
])
def test_timestamp_formats_parse_to_datetime(raw):
    assert isinstance(parse_timestamp(raw), dt.datetime)


def test_parser_returns_datetime_not_string():
    """Regression: a string here fails at the database boundary."""
    csv_text = "case_id,activity,timestamp,actor,system\nc1,do thing,2025-03-01T09:00:00,a@b.com,SAP"
    assert isinstance(parse_csv(csv_text)[0]["event_time"], dt.datetime)


def test_rows_with_unparseable_timestamps_are_skipped_not_crashing():
    csv_text = (
        "case_id,activity,timestamp,actor,system\n"
        "c1,good,2025-03-01T09:00:00,a@b.com,SAP\n"
        "c2,bad,not-a-date,a@b.com,SAP"
    )
    rows = parse_csv(csv_text)
    assert len(rows) == 1
    assert rows[0]["case_id"] == "c1"


# --------------------------------------------------------------------------
# End-to-end orchestration
# --------------------------------------------------------------------------

WORK_LOG = """case_id,activity,timestamp,actor,system
INV-1,Verify invoice against purchase order,2025-03-01T09:00:00,clerk@corp.com,SAP
INV-1,Match line items,2025-03-01T09:12:00,clerk@corp.com,Coupa
INV-1,Record verification result,2025-03-01T09:24:00,clerk@corp.com,SAP
INV-2,Verify invoice against purchase order,2025-03-02T09:00:00,clerk@corp.com,SAP
INV-2,Match line items,2025-03-02T09:10:00,clerk@corp.com,Coupa
INV-2,Record verification result,2025-03-02T09:26:00,clerk@corp.com,SAP
INV-3,Verify invoice against purchase order,2025-03-03T09:00:00,clerk@corp.com,SAP
INV-3,Match line items,2025-03-03T09:14:00,clerk@corp.com,Coupa
INV-3,Record verification result,2025-03-03T09:28:00,clerk@corp.com,SAP
PAY-1,Payroll tax remittance and filing,2025-03-01T11:00:00,lead@corp.com,ADP
PAY-1,Submit filing to tax authority,2025-03-01T11:22:00,lead@corp.com,IRS FIRE
PAY-2,Payroll tax remittance and filing,2025-03-02T11:00:00,lead@corp.com,ADP
PAY-2,Submit filing to tax authority,2025-03-02T11:20:00,lead@corp.com,IRS FIRE
PAY-3,Payroll tax remittance and filing,2025-03-03T11:00:00,lead@corp.com,ADP
PAY-3,Submit filing to tax authority,2025-03-03T11:25:00,lead@corp.com,IRS FIRE
"""


async def _ingest_and_discover(session_factory, csv_text=WORK_LOG):
    async with session_factory() as s:
        s.add_all([Event(**r) for r in parse_csv(csv_text)])
        await s.commit()
    async with session_factory() as s:
        return await run_discovery(s, settings=NO_LLM, min_cases=2)


async def test_discovery_creates_processes_from_a_csv(session_factory):
    result = await _ingest_and_discover(session_factory)
    assert result.processes_created >= 2


async def test_multi_step_case_becomes_one_process_not_three(session_factory):
    """Regression: clustering activity labels split one process into fragments."""
    result = await _ingest_and_discover(session_factory)
    names = " ".join(p["name"].lower() for p in result.processes)
    # Three invoice steps must not become three separate processes.
    assert result.processes_created == 2, result.processes
    assert "invoice" in names


async def test_sensitive_process_is_blocked_end_to_end(session_factory):
    """The headline guarantee, exercised through the real pipeline."""
    result = await _ingest_and_discover(session_factory)
    payroll = next(p for p in result.processes if "payroll" in p["name"].lower())
    assert payroll["risk_decision"] == RiskDecision.TOO_RISKY.value


async def test_ordinary_process_is_not_blocked(session_factory):
    result = await _ingest_and_discover(session_factory)
    invoice = next(p for p in result.processes if "invoice" in p["name"].lower())
    assert invoice["risk_decision"] == RiskDecision.PRE_APPROVED.value


async def test_discovered_processes_have_measured_not_zero_effort(session_factory):
    result = await _ingest_and_discover(session_factory)
    assert all(p["hours_per_month"] > 0 for p in result.processes)


async def test_every_event_is_attributed_to_its_process(session_factory):
    """An unattributed event would make the evidence trail incomplete."""
    await _ingest_and_discover(session_factory)
    async with session_factory() as s:
        orphans = (
            await s.execute(select(Event).where(Event.process_id.is_(None)))
        ).scalars().all()
    assert orphans == []


async def test_discovery_persists_scores_linked_to_weights(session_factory):
    await _ingest_and_discover(session_factory)
    async with session_factory() as s:
        scores = (await s.execute(select(Score))).scalars().all()
    assert scores
    assert all(sc.weights_id is not None for sc in scores)
    assert all(sc.reason for sc in scores)


async def test_rerunning_discovery_does_not_duplicate_processes(session_factory):
    """Only unattributed events are considered, so a second run is a no-op."""
    await _ingest_and_discover(session_factory)
    async with session_factory() as s:
        before = len((await s.execute(select(Process))).scalars().all())
        second = await run_discovery(s, settings=NO_LLM, min_cases=2)
        after = len((await s.execute(select(Process))).scalars().all())
    assert second.processes_created == 0
    assert before == after


async def test_discovery_on_empty_log_is_safe(session_factory):
    async with session_factory() as s:
        result = await run_discovery(s, settings=NO_LLM)
    assert result.processes_created == 0


async def test_single_case_noise_is_not_promoted_to_a_process(session_factory):
    """One-off work is noise, not a repetitive process worth automating."""
    one_off = (
        "case_id,activity,timestamp,actor,system\n"
        "X-1,Investigate unusual anomaly,2025-03-01T09:00:00,a@b.com,SAP\n"
        "X-1,Close investigation,2025-03-01T10:00:00,a@b.com,SAP\n"
    )
    result = await _ingest_and_discover(session_factory, one_off)
    assert result.processes_created == 0
