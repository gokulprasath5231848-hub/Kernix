"""Agent execution endpoint.

POST /api/processes/{id}/agent/run  — run the autonomous agent on a process.

The endpoint loads the process, its risk decision and (if present) its
generated blueprint, then hands them to the agent. The risk gate is enforced
inside the executor, but the outcome is also written to the existing AuditLog
so every autonomous action leaves a trail — the same audit surface the rest of
KINTIX already uses.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.executor import AgentRunResult, run_agent
from app.config import Settings, get_settings
from app.constants import RiskDecision
from app.database import get_db_session
from app.models import AuditLog, Blueprint, Process

router = APIRouter(prefix="/processes/{process_id}/agent", tags=["agent"])


def _blueprint_dict(blueprint: Optional[Blueprint], process: Process) -> dict:
    """Use the generated blueprint if there is one; otherwise synthesise a
    minimal one from the process so the agent always has something to execute."""
    if blueprint is not None:
        return {
            "trigger": blueprint.trigger,
            "steps": blueprint.steps,
            "estimated_savings_hours": blueprint.estimated_savings_hours,
        }
    # Fallback: one generic step per known process step, last one consequential.
    n = max(int(process.steps or 1), 1)
    systems = process.systems or ["source system"]
    steps = [
        {
            "name": f"Step {i + 1}",
            "description": f"Process work in {systems[i % len(systems)]}",
            "system": systems[i % len(systems)],
            "requires_approval": (i == n - 1),
            "approval_condition": "final consequential change",
        }
        for i in range(n)
    ]
    return {"trigger": "manual run", "steps": steps,
            "estimated_savings_hours": 0.0}


@router.post("/run", response_model=AgentRunResult)
async def run_process_agent(
    process_id: uuid.UUID,
    engine: str = Query("auto", pattern="^(auto|llm|scripted)$"),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    process = (
        await db.execute(select(Process).where(Process.id == process_id))
    ).scalar_one_or_none()
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    if not process.score:
        raise HTTPException(status_code=400, detail="Process must be scored first")

    risk_decision = RiskDecision(process.score.risk_decision)

    blueprint = (
        await db.execute(select(Blueprint).where(Blueprint.process_id == process_id))
    ).scalar_one_or_none()

    result = await run_agent(
        process_id=str(process_id),
        process_name=process.name,
        risk_decision=risk_decision,
        blueprint=_blueprint_dict(blueprint, process),
        settings=settings,
        engine=engine,
    )

    db.add(AuditLog(
        process_id=process_id,
        action=f"AGENT_{result.status.value}",
        actor="agent",
        detail=(
            f"engine={result.engine}; consequential_actions={result.actions_taken}; "
            f"{result.summary}"
        )[:900],
    ))
    await db.commit()

    return result
