"""Administrative actions. Guarded by the operator session token."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_db_session
from app.models import AuditLog, Blueprint, Event, Process, Score

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
async def reset_data(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_auth),
):
    """Wipe all ingested/discovered data so the console returns to an empty
    state. Deletes in foreign-key dependency order and preserves the scoring
    weights configuration."""
    for model in (AuditLog, Blueprint, Score, Event, Process):
        await session.execute(delete(model))
    await session.commit()
    logger.info("Data reset: all processes, events, scores, blueprints and audit logs cleared.")
    return {
        "status": "ok",
        "message": "All processes, work logs, scores, blueprints and audit entries have been cleared.",
    }
