"""Automation Blueprints catalog endpoint.

Returns a single flat list of every process with its current blueprint status,
reusing the existing Blueprint model and the existing generate / submit
endpoints in ``blueprints.py``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import RiskDecision
from app.database import get_db_session
from app.models import AuditLog, Blueprint, Process, Score
from app.schemas import BlueprintCatalogItem

router = APIRouter(prefix="/blueprints", tags=["blueprints-catalog"])


@router.get("", response_model=list[BlueprintCatalogItem])
async def list_blueprints(db: AsyncSession = Depends(get_db_session)):
    """List every process with its blueprint status.

    Status logic:
      TOO_RISKY                         → "Blocked"
      no blueprint                      → "Not Generated"
      blueprint + SUBMITTED_FOR_APPROVAL → "Awaiting Approval"
      blueprint, not submitted          → "Draft"
    """
    # 1. All processes with their eager-joined score
    processes = (
        await db.execute(select(Process).outerjoin(Process.score))
    ).scalars().all()

    # 2. All blueprints keyed by process_id (latest per process)
    bp_rows = (await db.execute(select(Blueprint))).scalars().all()
    bp_map: dict = {}
    for bp in bp_rows:
        existing = bp_map.get(bp.process_id)
        if existing is None or bp.generated_at > existing.generated_at:
            bp_map[bp.process_id] = bp

    # 3. Process IDs that have been submitted for approval
    submitted_rows = (
        await db.execute(
            select(AuditLog.process_id).where(
                AuditLog.action == "SUBMITTED_FOR_APPROVAL"
            )
        )
    ).scalars().all()
    submitted_ids = set(submitted_rows)

    # 4. Assemble catalog
    items: list[BlueprintCatalogItem] = []
    for proc in processes:
        score = proc.score
        risk = RiskDecision(score.risk_decision) if score else RiskDecision.TOO_RISKY
        value = score.value_score if score else 0.0
        bp = bp_map.get(proc.id)

        if risk == RiskDecision.TOO_RISKY:
            status = "Blocked"
        elif bp is None:
            status = "Not Generated"
        elif proc.id in submitted_ids:
            status = "Awaiting Approval"
        else:
            status = "Draft"

        items.append(BlueprintCatalogItem(
            process_id=proc.id,
            process_name=proc.name,
            department=proc.department,
            risk_decision=risk,
            value_score=value,
            blueprint_id=bp.id if bp else None,
            generated_at=bp.generated_at if bp else None,
            estimated_savings_hours=bp.estimated_savings_hours if bp else None,
            status=status,
        ))

    # Highest value first, blocked at the bottom
    items.sort(key=lambda i: (i.status == "Blocked", -i.value_score))
    return items
