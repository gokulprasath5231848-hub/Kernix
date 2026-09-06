from typing import Tuple
from app.constants import RiskDecision

def evaluate_risk(sensitive_outcome: bool, fully_rule_based: bool) -> Tuple[RiskDecision, str]:
    if sensitive_outcome:
        return RiskDecision.TOO_RISKY, "Process involves sensitive outcomes requiring human judgment"
    if not fully_rule_based:
        return RiskDecision.HUMAN_IN_THE_LOOP, "Process contains non-deterministic steps requiring human approval"
    return RiskDecision.PRE_APPROVED, "Process is fully rule-based with no sensitive outcomes"
