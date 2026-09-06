from enum import Enum

class RiskDecision(str, Enum):
    PRE_APPROVED = "PRE_APPROVED"
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"
    TOO_RISKY = "TOO_RISKY"

RISK_LABELS = {
    RiskDecision.PRE_APPROVED: "Pre-Approved",
    RiskDecision.HUMAN_IN_THE_LOOP: "Human-in-the-Loop",
    RiskDecision.TOO_RISKY: "Too Risky",
}

SCORING_WEIGHTS = {
    "frequency_volume": 0.25,
    "manual_time": 0.20,
    "rule_determinism": 0.20,
    "api_readiness": 0.15,
    "exception_frequency": 0.10,
    "privacy_risk": 0.10,
}

WEIGHT_FACTOR_NAMES = {
    "frequency_volume": "Frequency & Volume",
    "manual_time": "Manual Time",
    "rule_determinism": "Rule Determinism",
    "api_readiness": "API Readiness",
    "exception_frequency": "Exception Frequency",
    "privacy_risk": "Privacy Risk",
}

assert sum(SCORING_WEIGHTS.values()) == 1.0, "Scoring weights must sum to 1.0"
