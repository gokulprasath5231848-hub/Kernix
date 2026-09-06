from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db_session
from app.models import ScoringWeights
from app.schemas import WeightsResponse, WeightsUpdateRequest

router = APIRouter(prefix="/weights", tags=["weights"])

@router.get("", response_model=WeightsResponse)
async def get_weights(db: AsyncSession = Depends(get_db_session)):
    query = select(ScoringWeights).order_by(desc(ScoringWeights.effective_from)).limit(1)
    result = await db.execute(query)
    weights = result.scalar_one_or_none()
    
    if not weights:
        return WeightsResponse(id="00000000-0000-0000-0000-000000000000", weights={}, effective_from="2000-01-01T00:00:00Z", set_by="system")
        
    return WeightsResponse.model_validate(weights)

@router.put("", response_model=WeightsResponse)
async def update_weights(req: WeightsUpdateRequest, db: AsyncSession = Depends(get_db_session)):
    new_weights = ScoringWeights(weights=req.weights)
    db.add(new_weights)
    await db.commit()
    await db.refresh(new_weights)
    return WeightsResponse.model_validate(new_weights)
