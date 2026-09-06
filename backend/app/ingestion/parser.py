import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional, Union
from app.ingestion.normalizer import normalize_activity
from app.ingestion.pii_masker import get_masker

logger = logging.getLogger(__name__)

# Accepted timestamp layouts, tried in order. ISO-8601 first since it is what
# most exports produce.
_TIMESTAMP_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
)


def parse_timestamp(raw: str) -> Optional[datetime]:
    """Parse a timestamp into a timezone-aware datetime.

    Returns None when the value cannot be understood — the caller decides
    whether to skip the row. Returning a string here would blow up later at
    the database boundary, which is much harder to debug.
    """
    if not raw:
        return None
    value = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

def parse_csv(file_content: Union[str, bytes]) -> list[dict]:
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8', errors='replace')
        
    reader = csv.DictReader(io.StringIO(file_content))
    masker = get_masker()
    events = []
    
    expected_keys = {"case_id", "activity", "timestamp", "actor", "system"}
    
    for row_idx, row in enumerate(reader):
        try:
            if not expected_keys.issubset(set(row.keys())):
                logger.warning(f"Row {row_idx + 1} missing required keys. Skipping.")
                continue
                
            raw_activity = row.get("activity", "")
            actor = row.get("actor", "")
            
            activity_normalised = normalize_activity(raw_activity)
            actor_masked = masker.mask_text(actor)
            
            # calculate confidence based on completeness
            fields_present = sum(1 for k in expected_keys if row.get(k, "").strip() != "")
            confidence = fields_present / len(expected_keys)
            
            event_time = parse_timestamp(row.get("timestamp", ""))
            if event_time is None:
                logger.warning(
                    f"Row {row_idx + 1}: unparseable timestamp "
                    f"{row.get('timestamp')!r}. Skipping."
                )
                continue

            events.append({
                "case_id": row["case_id"].strip(),
                "activity_raw": raw_activity.strip(),
                "activity_normalised": activity_normalised,
                "event_time": event_time,
                "actor_masked": actor_masked,
                "system": row["system"].strip(),
                "confidence": confidence
            })
        except Exception as e:
            logger.warning(f"Error parsing row {row_idx + 1}: {e}. Skipping.")
            
    return events
