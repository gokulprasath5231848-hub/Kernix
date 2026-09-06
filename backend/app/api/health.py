import datetime
from fastapi import APIRouter, Depends
from app.config import Settings, get_settings

router = APIRouter()

@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "version": settings.API_VERSION,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
