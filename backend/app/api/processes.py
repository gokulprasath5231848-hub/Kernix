from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import datetime
import uuid

from app.database import get_db_session
from app.models import Process, Event, Score, ScoringWeights, AuditLog
from app.schemas import ProcessListResponse, ProcessDetail, ProcessListItem
from app.constants import RiskDecision, SCORING_WEIGHTS
from app.scoring.engine import compute_value_score
from app.scoring.risk_gate import evaluate_risk

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
    score.scored_at = datetime.datetime.now(datetime.timezone.utc)
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
