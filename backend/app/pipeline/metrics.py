"""Derive quantitative scoring factors from a real event log.

This is the piece that turns discovered activity clusters into the six numeric
factors the scoring engine consumes. Everything here is deterministic and
computed in Python — no LLM involved. The semantic layer may only supply
*qualitative* signals (see ``semantic.py``); the numbers come from the data.
"""
from __future__ import annotations

import logging
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Sequence

logger = logging.getLogger(__name__)

# Systems with well-known, automatable APIs score higher on api_readiness.
# Deliberately a small, editable list rather than an LLM judgement — this
# feeds a number, and numbers must be reproducible.
API_READY_SYSTEMS = {
    "sap", "workday", "coupa", "netsuite", "salesforce", "servicenow",
    "jira", "zendesk", "slack", "okta", "active directory", "google ws",
    "docusign", "hris", "oracle", "quickbooks", "xero", "outlook",
}

# Activity wording that indicates a case was reworked rather than completed
# cleanly. Used for exception_frequency.
REWORK_MARKERS = (
    "rework", "correct", "fix", "reject", "retry", "resubmit", "escalat",
    "dispute", "exception", "error", "amend", "revert", "duplicate",
)

# A case is treated as a month's worth of demand when the log is shorter than
# this; avoids dividing by a near-zero window and producing absurd rates.
MIN_WINDOW_DAYS = 1.0


@dataclass
class ProcessMetrics:
    """Measured properties of one discovered process."""

    case_count: int
    distinct_actors: int
    systems: list[str]
    step_count: int
    cases_per_month: float
    avg_minutes_per_case: float
    total_hours_per_month: float
    rework_rate: float
    factors: dict[str, float] = field(default_factory=dict)


def _span_days(times: Sequence[datetime]) -> float:
    if len(times) < 2:
        return MIN_WINDOW_DAYS
    delta = (max(times) - min(times)).total_seconds() / 86400.0
    return max(delta, MIN_WINDOW_DAYS)


def _case_duration_minutes(times: Sequence[datetime]) -> float:
    """Handling time for a case: first touch to last touch.

    Single-event cases have no measurable duration, so they contribute nothing
    rather than a fabricated estimate.
    """
    if len(times) < 2:
        return 0.0
    return (max(times) - min(times)).total_seconds() / 60.0


def _scale(value: float, full_marks_at: float) -> float:
    """Map a raw measurement onto 0-100, saturating at ``full_marks_at``."""
    if full_marks_at <= 0:
        return 0.0
    return max(0.0, min(100.0, (value / full_marks_at) * 100.0))


def compute_process_metrics(events: Iterable) -> ProcessMetrics:
    """Measure one process from the events attributed to it.

    ``events`` must expose ``case_id``, ``event_time``, ``system`` and
    ``activity_normalised`` (i.e. ORM Event rows, or any equivalent object).
    """
    events = list(events)
    if not events:
        return ProcessMetrics(
            case_count=0, distinct_actors=0, systems=[], step_count=0,
            cases_per_month=0.0, avg_minutes_per_case=0.0,
            total_hours_per_month=0.0, rework_rate=0.0,
            factors={k: 0.0 for k in (
                "frequency_volume", "manual_time", "rule_determinism",
                "api_readiness", "exception_frequency", "privacy_risk")},
        )

    by_case: dict[str, list] = defaultdict(list)
    for e in events:
        by_case[e.case_id].append(e)

    all_times = [e.event_time for e in events if e.event_time]
    window_days = _span_days(all_times)

    case_count = len(by_case)
    cases_per_month = case_count * (30.0 / window_days)

    durations = [
        _case_duration_minutes(sorted(e.event_time for e in evs if e.event_time))
        for evs in by_case.values()
    ]
    measurable = [d for d in durations if d > 0]
    avg_minutes = statistics.mean(measurable) if measurable else 0.0

    systems = sorted({e.system for e in events if e.system})
    actors = {getattr(e, "actor_masked", None) for e in events}
    actors.discard(None)

    step_counts = [len(evs) for evs in by_case.values()]
    step_count = int(round(statistics.mean(step_counts))) if step_counts else 0

    # Rework: a case is reworked if any activity matches a marker, or if the
    # same activity occurs more than once within the case.
    reworked = 0
    for evs in by_case.values():
        labels = [(e.activity_normalised or "").lower() for e in evs]
        if any(any(m in lab for m in REWORK_MARKERS) for lab in labels):
            reworked += 1
        elif len(labels) != len(set(labels)):
            reworked += 1
    rework_rate = reworked / case_count if case_count else 0.0

    total_hours_per_month = (cases_per_month * avg_minutes) / 60.0

    known = sum(1 for s in systems if s.strip().lower() in API_READY_SYSTEMS)
    api_readiness = _scale(known, max(len(systems), 1)) if systems else 40.0

    factors = {
        # 200 cases/month is treated as maximum volume pressure.
        "frequency_volume": round(_scale(cases_per_month, 200.0), 1),
        # 60 minutes of handling is treated as maximally expensive.
        "manual_time": round(_scale(avg_minutes, 60.0), 1),
        # Placeholder: overwritten by the semantic layer, which judges how
        # rule-based the work is. Kept here so the factor set is always
        # complete even if semantic analysis is unavailable.
        "rule_determinism": 50.0,
        "api_readiness": round(api_readiness, 1),
        # Inverted: FEWER exceptions is better, so a low rework rate scores high.
        "exception_frequency": round(max(0.0, 100.0 - rework_rate * 100.0), 1),
        # Placeholder: overwritten by the semantic layer.
        "privacy_risk": 50.0,
    }

    return ProcessMetrics(
        case_count=case_count,
        distinct_actors=len(actors),
        systems=systems,
        step_count=step_count,
        cases_per_month=round(cases_per_month, 1),
        avg_minutes_per_case=round(avg_minutes, 1),
        total_hours_per_month=round(total_hours_per_month, 1),
        rework_rate=round(rework_rate, 3),
        factors=factors,
    )


def summarise_activities(events: Iterable, limit: int = 8) -> list[str]:
    """Most common raw activity labels — used as context for the LLM prompt."""
    counter = Counter(
        (e.activity_raw or "").strip() for e in events if (e.activity_raw or "").strip()
    )
    return [label for label, _ in counter.most_common(limit)]
