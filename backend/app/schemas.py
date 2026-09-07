from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import datetime
import uuid
from app.constants import RiskDecision

class EventResponse(BaseModel):
    id: uuid.UUID
    case_id: str
    activity_raw: str
    activity_normalised: str
    event_time: datetime.datetime
    actor_masked: str
    system: str
    confidence: float
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class ScoreDetail(BaseModel):
    id: uuid.UUID
    process_id: uuid.UUID
    frequency_volume: float
    manual_time: float
    rule_determinism: float
    api_readiness: float
    exception_frequency: float
    privacy_risk: float
    value_score: float
    sensitive_outcome: bool
    fully_rule_based: bool
    risk_decision: RiskDecision
    reason: Optional[str] = None
    scored_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class ProcessListItem(BaseModel):
    id: uuid.UUID
    name: str
    department: Optional[str]
    cases_per_month: int
    steps: int
    systems_touched: int
    systems: List[str]
    score: Optional[ScoreDetail] = None
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class ProcessDetail(BaseModel):
    id: uuid.UUID
    name: str
    department: Optional[str]
    cases_per_month: int
    steps: int
    systems_touched: int
    systems: List[str]
    score: Optional[ScoreDetail] = None
    evidence_trail: List[EventResponse] = []
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class ProcessListResponse(BaseModel):
    items: List[ProcessListItem]
    total_count: int

class BlueprintStepResponse(BaseModel):
    name: str
    description: str
    system: str
    requires_approval: bool = False
    approval_condition: Optional[str] = None

class BlueprintResponse(BaseModel):
    id: uuid.UUID
    process_id: uuid.UUID
    steps: List[BlueprintStepResponse]
    trigger: str
    estimated_savings_hours: float
    generated_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class WeightsResponse(BaseModel):
    id: uuid.UUID
    weights: dict
    effective_from: datetime.datetime
    set_by: str
    model_config = ConfigDict(from_attributes=True)

class WeightsUpdateRequest(BaseModel):
    weights: dict

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    process_id: Optional[uuid.UUID]
    action: str
    actor: str
    detail: Optional[str]
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Automation Blueprints catalog
# ---------------------------------------------------------------------------

class BlueprintCatalogItem(BaseModel):
    process_id: uuid.UUID
    process_name: str
    department: Optional[str]
    risk_decision: RiskDecision
    value_score: float
    blueprint_id: Optional[uuid.UUID] = None
    generated_at: Optional[datetime.datetime] = None
    estimated_savings_hours: Optional[float] = None
    status: str   # "Blocked" | "Not Generated" | "Draft" | "Awaiting Approval"


# ---------------------------------------------------------------------------
# Process Intelligence (process mining)
# ---------------------------------------------------------------------------

class FlowNode(BaseModel):
    activity: str
    count: int
    avg_minutes: float
    systems: List[str]

class FlowEdge(BaseModel):
    source: str
    target: str
    count: int

class FlowVariant(BaseModel):
    sequence: List[str]
    case_count: int
    pct: float

class ProcessIntelligence(BaseModel):
    process_id: uuid.UUID
    name: str
    case_count: int
    nodes: List[FlowNode]
    edges: List[FlowEdge]
    variants: List[FlowVariant]
    rework_rate: float
