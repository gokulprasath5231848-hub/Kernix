from app.constants import RiskDecision

class BlueprintForbiddenError(Exception):
    def __init__(self, process_id: str, reason: str):
        super().__init__(reason)
        self.process_id = process_id
        self.reason = reason

def check_blueprint_allowed(risk_decision: RiskDecision, process_id: str = "") -> None:
    if risk_decision == RiskDecision.TOO_RISKY:
        raise BlueprintForbiddenError(process_id, "Blueprint generation is forbidden for TOO_RISKY processes.")
