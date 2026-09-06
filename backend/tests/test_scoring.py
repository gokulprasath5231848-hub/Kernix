import math
from app.scoring.engine import compute_value_score
from app.scoring.risk_gate import evaluate_risk
from app.constants import RiskDecision, SCORING_WEIGHTS

def test_weighted_formula_is_deterministic():
    factors = {"frequency_volume": 100, "manual_time": 100, "rule_determinism": 100, "api_readiness": 100, "exception_frequency": 100, "privacy_risk": 100}
    score1 = compute_value_score(factors, SCORING_WEIGHTS)
    score2 = compute_value_score(factors, SCORING_WEIGHTS)
    assert score1 == score2

def test_high_score_does_not_bypass_risk_gate():
    decision, reason = evaluate_risk(sensitive_outcome=True, fully_rule_based=True)
    assert decision == RiskDecision.TOO_RISKY
    assert "sensitive outcomes" in reason

def test_non_rule_based_requires_hitl():
    decision, reason = evaluate_risk(sensitive_outcome=False, fully_rule_based=False)
    assert decision == RiskDecision.HUMAN_IN_THE_LOOP

def test_safe_process():
    decision, reason = evaluate_risk(sensitive_outcome=False, fully_rule_based=True)
    assert decision == RiskDecision.PRE_APPROVED

def test_weights_sum_to_100():
    assert math.isclose(sum(SCORING_WEIGHTS.values()), 1.0, abs_tol=0.001)

def test_score_clamped_to_0_100():
    factors = {"frequency_volume": 200, "manual_time": 200, "rule_determinism": 200, "api_readiness": 200, "exception_frequency": 200, "privacy_risk": 200}
    score = compute_value_score(factors, SCORING_WEIGHTS)
    assert score <= 100.0

def test_risk_gate_ignores_score():
    import inspect
    sig = inspect.signature(evaluate_risk)
    assert "score" not in sig.parameters
