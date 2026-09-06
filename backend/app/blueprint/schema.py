from pydantic import BaseModel, Field
from typing import List, Optional
from app.constants import RiskDecision

class BlueprintStep(BaseModel):
    name: str
    description: str
    system: str
    requires_approval: bool = False
    approval_condition: Optional[str] = None

class BlueprintSchema(BaseModel):
    steps: List[BlueprintStep]
    trigger: str
    estimated_savings_hours: float

def validate_hitl_blueprint(blueprint: BlueprintSchema, risk_decision: RiskDecision) -> bool:
    if risk_decision == RiskDecision.HUMAN_IN_THE_LOOP:
        return any(step.requires_approval for step in blueprint.steps)
    return True
