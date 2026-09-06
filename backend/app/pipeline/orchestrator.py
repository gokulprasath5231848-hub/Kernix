"""End-to-end discovery orchestration.

This is the module that was missing: it connects the components that already
existed but were never wired together.

    unattributed events
        -> group by normalised activity
        -> embed (discovery.EmbeddingService)
        -> cluster (clustering.cluster_activities)
        -> measure (metrics.compute_process_metrics)      [deterministic]
        -> interpret (semantic.analyse_process)           [LLM + policy]
        -> score (scoring.engine.compute_value_score)     [deterministic]
        -> gate (scoring.risk_gate.evaluate_risk)         [deterministic]
        -> persist Process + Score, attach Events

Division of responsibility, deliberately:
the LLM interprets, Python measures, and Python alone decides.
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.constants import SCORING_WEIGHTS
from app.models import AuditLog, Event, Process, Score, ScoringWeights
from app.pipeline.clustering import cluster_activities
from app.pipeline.discovery import get_embedding_service
from app.pipeline.metrics import compute_process_metrics, summarise_activities
from app.pipeline.semantic import analyse_process
from app.scoring.engine import compute_value_score
from app.scoring.risk_gate import evaluate_risk

logger = logging.getLogger(__name__)

# Clusters seen fewer times than this are noise, not processes.
MIN_CASES_FOR_PROCESS = 2


@dataclass
class DiscoveryResult:
    events_considered: int
    clusters_found: int
    processes_created: int
    processes: list[dict]

    def as_dict(self) -> dict:
        return {
            "events_considered": self.events_considered,
            "clusters_found": self.clusters_found,
            "processes_created": self.processes_created,
            "processes": self.processes,
        }


async def _active_weights(db: AsyncSession) -> tuple[dict, Optional[object]]:
    row = (
        await db.execute(
            select(ScoringWeights).order_by(ScoringWeights.effective_from.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        row = ScoringWeights(weights=SCORING_WEIGHTS, set_by="discovery")
        db.add(row)
        await db.flush()
    return row.weights, row


async def run_discovery(
    db: AsyncSession,
    *,
    settings: Optional[Settings] = None,
    min_cases: int = MIN_CASES_FOR_PROCESS,
    only_unattributed: bool = True,
) -> DiscoveryResult:
    """Discover processes from the event log and persist them.

    Only events not already attached to a process are considered by default,
    so re-running after a second upload is additive rather than destructive.
    """
    settings = settings or get_settings()

    query = select(Event)
    if only_unattributed:
        query = query.where(Event.process_id.is_(None))
    events = list((await db.execute(query)).scalars().all())

    if not events:
        return DiscoveryResult(0, 0, 0, [])

    # --- build a trace per case --------------------------------------------
    # A process is a *flow of work across a case*, not a single activity. If we
    # clustered individual activity labels we would split one invoice process
    # into "verify invoice" / "match lines" / "record result" — three fragments
    # rather than one process — and per-case duration would be unmeasurable.
    # So each case is reduced to its ordered activity trace, and the traces are
    # what get embedded and clustered.
    cases: dict[str, list[Event]] = {}
    for e in events:
        cases.setdefault(e.case_id, []).append(e)

    case_ids: list[str] = []
    trace_texts: list[str] = []
    for case_id, case_events in cases.items():
        case_events.sort(key=lambda ev: (ev.event_time is None, ev.event_time))
        # Deduplicate consecutive repeats so a retry doesn't create a
        # structurally different trace.
        steps: list[str] = []
        for ev in case_events:
            label = (ev.activity_normalised or ev.activity_raw or "").strip()
            if label and (not steps or steps[-1] != label):
                steps.append(label)
        if not steps:
            continue
        case_ids.append(case_id)
        trace_texts.append(" > ".join(steps))

    if not case_ids:
        return DiscoveryResult(len(events), 0, 0, [])

    embeddings = get_embedding_service().embed(trace_texts)
    clusters = cluster_activities(trace_texts, embeddings)
    logger.info(
        "Discovery: %d cases -> %d trace clusters", len(case_ids), len(clusters)
    )

    # Map each trace text back to the cases that produced it.
    trace_to_cases: dict[str, list[str]] = {}
    for case_id, trace in zip(case_ids, trace_texts):
        trace_to_cases.setdefault(trace, []).append(case_id)

    weights, weights_row = await _active_weights(db)

    created: list[dict] = []
    for cluster in clusters:
        cluster_events: list[Event] = []
        for trace in set(cluster["labels"]):
            for case_id in trace_to_cases.get(trace, []):
                cluster_events.extend(cases.get(case_id, []))
        if not cluster_events:
            continue

        metrics = compute_process_metrics(cluster_events)
        if metrics.case_count < min_cases:
            logger.debug(
                "Skipping cluster %r: only %d case(s), below min_cases=%d",
                cluster["name"][:60], metrics.case_count, min_cases,
            )
            continue

        activities = summarise_activities(cluster_events)
        # The cluster "name" is a trace string ("a > b > c"). Without an LLM to
        # supply a canonical name, the FIRST step of the dominant trace names
        # the process better than its most frequent step: a process is best
        # identified by what triggers it, not by its busiest internal step.
        dominant_trace = Counter(cluster["labels"]).most_common(1)[0][0]
        first_step = dominant_trace.split(" > ")[0].strip()
        fallback_name = (first_step or (activities[0] if activities else cluster["name"])).title()

        # LLM interprets; policy hardens the result so it can only be safer.
        analysis = await analyse_process(
            cluster_name=fallback_name,
            activities=activities,
            systems=metrics.systems,
            cases=metrics.case_count,
            avg_minutes=metrics.avg_minutes_per_case,
            rework_rate=metrics.rework_rate,
            settings=settings,
        )

        # Qualitative signals feed only the two judgement-shaped factors.
        # Everything else stays measured.
        factors = dict(metrics.factors)
        factors["rule_determinism"] = float(analysis.determinism_score)
        factors["privacy_risk"] = 10.0 if analysis.sensitive_outcome else 85.0

        value_score = compute_value_score(factors, weights)

        # The gate. Takes no score — it cannot be influenced by one.
        decision, reason = evaluate_risk(
            sensitive_outcome=analysis.sensitive_outcome,
            fully_rule_based=analysis.rule_based,
        )

        process = Process(
            name=analysis.canonical_process_name or fallback_name,
            department=None,
            cases_per_month=int(round(metrics.cases_per_month)),
            steps=metrics.step_count,
            systems_touched=len(metrics.systems),
            systems=metrics.systems or list(analysis.systems_involved),
        )
        db.add(process)
        await db.flush()

        db.add(Score(
            process_id=process.id,
            frequency_volume=factors["frequency_volume"],
            manual_time=factors["manual_time"],
            rule_determinism=factors["rule_determinism"],
            api_readiness=factors["api_readiness"],
            exception_frequency=factors["exception_frequency"],
            privacy_risk=factors["privacy_risk"],
            value_score=value_score,
            sensitive_outcome=analysis.sensitive_outcome,
            fully_rule_based=analysis.rule_based,
            risk_decision=decision.value,
            reason=reason,
            weights_id=weights_row.id if weights_row else None,
        ))

        # Attribute the evidence, so the trail on the detail page is real.
        for e in cluster_events:
            e.process_id = process.id

        db.add(AuditLog(
            process_id=process.id,
            action="DISCOVERED",
            actor="pipeline",
            detail=(
                f"Discovered from {metrics.case_count} cases across "
                f"{len(set(cluster['labels']))} trace variant(s); "
                f"score={value_score}; risk={decision.value}; {analysis.reasoning}"[:900]
            ),
        ))

        created.append({
            "id": str(process.id),
            "name": process.name,
            "cases_per_month": metrics.cases_per_month,
            "hours_per_month": metrics.total_hours_per_month,
            "value_score": value_score,
            "risk_decision": decision.value,
            "reason": reason,
            "systems": metrics.systems,
        })

    await db.commit()

    return DiscoveryResult(
        events_considered=len(events),
        clusters_found=len(clusters),
        processes_created=len(created),
        processes=created,
    )
