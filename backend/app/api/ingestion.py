import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db_session
from app.ingestion.parser import parse_csv
from app.models import Event
from app.pipeline.orchestrator import run_discovery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("")
async def ingest_events(
    file: UploadFile,
    discover: bool = Query(
        True,
        description=(
            "Run process discovery over the newly ingested events. "
            "Set false to only store the raw event log."
        ),
    ),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    """Ingest a work-log CSV and (by default) discover processes from it.

    Expected columns: case_id, activity, timestamp, actor, system.
    PII is masked during parsing, before anything is written to the database.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    events_data = parse_csv(content)
    if not events_data:
        raise HTTPException(
            status_code=400,
            detail=(
                "No usable rows found. Required columns: "
                "case_id, activity, timestamp, actor, system"
            ),
        )

    db.add_all([Event(**ed) for ed in events_data])
    await db.commit()

    result = {
        "message": f"Ingested {len(events_data)} events.",
        "events_ingested": len(events_data),
    }

    if discover:
        discovery = await run_discovery(db, settings=settings)
        result["discovery"] = discovery.as_dict()
        result["message"] += f" Discovered {discovery.processes_created} process(es)."

    return result


@router.post("/discover")
async def discover_processes(
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    """Run discovery over any events not yet attributed to a process.

    Useful after uploading with ?discover=false, or to re-run once a
    GROQ_API_KEY has been configured.
    """
    discovery = await run_discovery(db, settings=settings)
    return discovery.as_dict()
