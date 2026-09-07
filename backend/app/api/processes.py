from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from collections import Counter, defaultdict
import datetime
import statistics
import uuid

from app.database import get_db_session
from app.models import Process, Event, Score, ScoringWeights, AuditLog
from app.schemas import (
    ProcessListResponse, ProcessDetail, ProcessListItem,
    ProcessIntelligence, FlowNode, FlowEdge, FlowVariant,
)
from app.constants import RiskDecision, SCORING_WEIGHTS
from app.scoring.engine import compute_value_score
from app.scoring.risk_gate import evaluate_risk
from app.pipeline.metrics import REWORK_MARKERS

router = APIRouter(prefix="/processes", tags=["processes"])

@router.get("", response_model=ProcessListResponse)
async def list_processes(
    risk_class: Optional[RiskDecision] = Query(None),
    sort_by: str = Query("value_score"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session)
):
    query = select(Process).outerjoin(Process.score)
    
    if risk_class:
        query = query.where(Score.risk_decision == risk_class.value)
        
    result = await db.execute(query)
    processes = result.scalars().all()
    
    # Python level sort
    if sort_by == "value_score":
        processes.sort(key=lambda p: p.score.value_score if p.score else 0, reverse=True)
    elif sort_by == "frequency":
        processes.sort(key=lambda p: p.cases_per_month, reverse=True)
        
    total = len(processes)
    page = processes[offset: offset + limit]
    items = [ProcessListItem.model_validate(p) for p in page]
    return ProcessListResponse(items=items, total_count=total)

@router.get("/{process_id}", response_model=ProcessDetail)
async def get_process(process_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    query = select(Process).where(Process.id == process_id)
    result = await db.execute(query)
    process = result.scalar_one_or_none()
    
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
        
    # Evidence trail: only the events belonging to THIS process. The score's
    # credibility rests on this being the real provenance, not a sample.
    events_query = (
        select(Event)
        .where(Event.process_id == process_id)
        .order_by(Event.event_time.desc())
        .limit(20)
    )
    events_result = await db.execute(events_query)
    events = events_result.scalars().all()

    process_dict = ProcessDetail.model_validate(process).model_dump()
    process_dict["evidence_trail"] = events
    return process_dict

@router.post("/{process_id}/reevaluate")
async def reevaluate_process(process_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    query = select(Process).where(Process.id == process_id)
    result = await db.execute(query)
    process = result.scalar_one_or_none()

    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    if not process.score:
        raise HTTPException(status_code=400, detail="Process has no score to re-evaluate")

    # Re-score against the CURRENTLY ACTIVE weights, so an admin weight change
    # is reflected on re-evaluation. Old scores stay explainable via weights_id.
    weights_row = (
        await db.execute(select(ScoringWeights).order_by(ScoringWeights.effective_from.desc()).limit(1))
    ).scalar_one_or_none()
    active_weights = weights_row.weights if weights_row else SCORING_WEIGHTS

    score = process.score
    factors = {
        "frequency_volume": score.frequency_volume,
        "manual_time": score.manual_time,
        "rule_determinism": score.rule_determinism,
        "api_readiness": score.api_readiness,
        "exception_frequency": score.exception_frequency,
        "privacy_risk": score.privacy_risk,
    }
    new_value_score = compute_value_score(factors, active_weights)

    # Risk is re-derived from the gate, never carried over or inferred from the score.
    decision, reason = evaluate_risk(
        sensitive_outcome=score.sensitive_outcome,
        fully_rule_based=score.fully_rule_based,
    )

    score.value_score = new_value_score
    score.risk_decision = decision.value
    score.reason = reason
    # scores.scored_at is TIMESTAMP WITHOUT TIME ZONE, so store a naive UTC value.
    # A tz-aware datetime here makes asyncpg raise "can't subtract offset-naive
    # and offset-aware datetimes" and the endpoint 500s.
    score.scored_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if weights_row:
        score.weights_id = weights_row.id

    db.add(AuditLog(
        process_id=process.id,
        action="REEVALUATE",
        actor="api",
        detail=f"Re-scored to {new_value_score} · risk={decision.value}",
    ))
    await db.commit()

    return {
        "status": "reevaluated",
        "process_id": str(process.id),
        "value_score": new_value_score,
        "risk_decision": decision.value,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Process Intelligence — trace-based process mining
# ---------------------------------------------------------------------------

@router.get("/{process_id}/intelligence", response_model=ProcessIntelligence)
async def get_process_intelligence(
    process_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Compute flow graph, path variants, and bottlenecks from events."""

    process = (
        await db.execute(select(Process).where(Process.id == process_id))
    ).scalar_one_or_none()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")

    events = (
        await db.execute(
            select(Event)
            .where(Event.process_id == process_id)
            .order_by(Event.event_time)
        )
    ).scalars().all()

    if not events:
        return ProcessIntelligence(
            process_id=process.id,
            name=process.name,
            case_count=0,
            nodes=[],
            edges=[],
            variants=[],
            rework_rate=0.0,
        )

    # --- group events by case, sort by time --------------------------------
    cases: dict[str, list] = defaultdict(list)
    for e in events:
        cases[e.case_id].append(e)

    traces: list[tuple[str, ...]] = []
    # Per-activity aggregation buckets
    activity_count: Counter = Counter()
    activity_durations: dict[str, list[float]] = defaultdict(list)
    activity_systems: dict[str, set[str]] = defaultdict(set)
    edge_count: Counter = Counter()
    reworked = 0

    for case_events in cases.values():
        case_events.sort(key=lambda ev: (ev.event_time is None, ev.event_time))

        # Build deduped trace (same consecutive-repeat logic as orchestrator)
        steps: list[str] = []
        for ev in case_events:
            label = (ev.activity_normalised or ev.activity_raw or "").strip()
            if label and (not steps or steps[-1] != label):
                steps.append(label)

        if not steps:
            continue

        traces.append(tuple(steps))

        # Node stats
        for i, ev in enumerate(case_events):
            label = (ev.activity_normalised or ev.activity_raw or "").strip()
            if not label:
                continue
            activity_count[label] += 1
            if ev.system:
                activity_systems[label].add(ev.system)
            # Duration = Δ to next event in the same case
            if i + 1 < len(case_events) and ev.event_time and case_events[i + 1].event_time:
                delta_min = (case_events[i + 1].event_time - ev.event_time).total_seconds() / 60.0
                if delta_min >= 0:
                    activity_durations[label].append(delta_min)

        # Edge stats (on deduped trace)
        for a, b in zip(steps, steps[1:]):
            edge_count[(a, b)] += 1

        # Rework detection (same logic as metrics.py)
        labels = [(ev.activity_normalised or "").lower() for ev in case_events]
        if any(any(m in lab for m in REWORK_MARKERS) for lab in labels):
            reworked += 1
        elif len(labels) != len(set(labels)):
            reworked += 1

    case_count = len(traces)
    rework_rate = round(reworked / case_count, 3) if case_count else 0.0

    # --- assemble nodes ----------------------------------------------------
    nodes = [
        FlowNode(
            activity=act,
            count=cnt,
            avg_minutes=round(
                statistics.mean(activity_durations[act]), 1
            ) if activity_durations.get(act) else 0.0,
            systems=sorted(activity_systems.get(act, set())),
        )
        for act, cnt in activity_count.most_common()
    ]

    # --- assemble edges ----------------------------------------------------
    edges = [
        FlowEdge(source=src, target=tgt, count=cnt)
        for (src, tgt), cnt in edge_count.most_common()
    ]

    # --- assemble variants (top 20) ----------------------------------------
    variant_counter = Counter(traces)
    variants = [
        FlowVariant(
            sequence=list(seq),
            case_count=cnt,
            pct=round(cnt / case_count * 100, 1),
        )
        for seq, cnt in variant_counter.most_common(20)
    ]

    return ProcessIntelligence(
        process_id=process.id,
        name=process.name,
        case_count=case_count,
        nodes=nodes,
        edges=edges,
        variants=variants,
        rework_rate=rework_rate,
    )

