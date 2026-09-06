from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
import uuid

from app.database import get_db_session
from app.models import AuditLog
from app.schemas import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("", response_model=List[AuditLogResponse])
async def get_audit_logs(
    process_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db_session)
):
    query = select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit).offset(offset)
    
    if process_id:
        query = query.where(AuditLog.process_id == process_id)
        
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [AuditLogResponse.model_validate(log) for log in logs]
