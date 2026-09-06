from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db_session
from app.config import Settings, get_settings
from app.models import Process, Blueprint, AuditLog
from app.schemas import BlueprintResponse
from app.blueprint.generator import generate_blueprint, BlueprintGenerationError
from app.blueprint.preconditions import BlueprintForbiddenError
from app.constants import RiskDecision

router = APIRouter(prefix="/processes/{process_id}/blueprint", tags=["blueprints"])

@router.get("", response_model=BlueprintResponse)
async def get_blueprint(process_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    process_query = select(Process).where(Process.id == process_id)
    result = await db.execute(process_query)
    process = result.scalar_one_or_none()
    
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
        
    if process.score and process.score.risk_decision == RiskDecision.TOO_RISKY.value:
        raise HTTPException(status_code=403, detail="Blueprint generation forbidden for TOO_RISKY processes")
        
    blueprint_query = select(Blueprint).where(Blueprint.process_id == process_id)
    bp_result = await db.execute(blueprint_query)
    blueprint = bp_result.scalar_one_or_none()
    
    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")
        
    return BlueprintResponse.model_validate(blueprint)

@router.post("/submit-for-approval")
async def submit_for_approval(process_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    """Queue a blueprint for human authorisation.

    KINTIX never executes an automation. This records the request in the audit
    log for a human to action; it changes nothing in any source system.
    """
    process = (
        await db.execute(select(Process).where(Process.id == process_id))
    ).scalar_one_or_none()

    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    if not process.score:
        raise HTTPException(status_code=400, detail="Process must be scored first")

    # The gate is re-checked here, independently of the GET endpoint.
    if process.score.risk_decision == RiskDecision.TOO_RISKY.value:
        raise HTTPException(
            status_code=403,
            detail="Cannot queue a TOO_RISKY process for automation approval",
        )

    blueprint = (
        await db.execute(select(Blueprint).where(Blueprint.process_id == process_id))
    ).scalar_one_or_none()
    if not blueprint:
        raise HTTPException(status_code=404, detail="No blueprint to submit")

    db.add(AuditLog(
        process_id=process_id,
        action="SUBMITTED_FOR_APPROVAL",
        actor="api",
        detail=f"Blueprint {blueprint.id} queued for human authorisation",
    ))
    await db.commit()

    return {"status": "awaiting_human_approval", "process_id": str(process_id)}


@router.post("/generate", response_model=BlueprintResponse)
async def trigger_blueprint_generation(
    process_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings)
):
    process_query = select(Process).where(Process.id == process_id)
    result = await db.execute(process_query)
    process = result.scalar_one_or_none()
    
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
        
    if not process.score:
        raise HTTPException(status_code=400, detail="Process must be scored first")
        
    try:
        risk_decision = RiskDecision(process.score.risk_decision)
        schema = await generate_blueprint(
            process_name=process.name,
            process_description=f"Department: {process.department}, Steps: {process.steps}",
            systems=process.systems,
            risk_decision=risk_decision,
            settings=settings
        )
        
        blueprint = Blueprint(
            process_id=process_id,
            steps=[s.model_dump() for s in schema.steps],
            trigger=schema.trigger,
            estimated_savings_hours=schema.estimated_savings_hours
        )
        db.add(blueprint)
        await db.commit()
        await db.refresh(blueprint)
        
        return BlueprintResponse.model_validate(blueprint)
    except BlueprintForbiddenError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except BlueprintGenerationError as e:
        raise HTTPException(status_code=500, detail=str(e))
