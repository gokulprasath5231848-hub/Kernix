import pytest
from app.blueprint.preconditions import check_blueprint_allowed, BlueprintForbiddenError
from app.blueprint.schema import BlueprintSchema, BlueprintStep, validate_hitl_blueprint
from app.constants import RiskDecision

def test_precondition_blocks_too_risky():
    with pytest.raises(BlueprintForbiddenError):
        check_blueprint_allowed(RiskDecision.TOO_RISKY)

def test_precondition_allows_safe():
    check_blueprint_allowed(RiskDecision.PRE_APPROVED) # Should not raise

def test_precondition_allows_hitl():
    check_blueprint_allowed(RiskDecision.HUMAN_IN_THE_LOOP) # Should not raise

def test_hitl_blueprint_requires_approval_step():
    schema = BlueprintSchema(
        trigger="test",
        estimated_savings_hours=1.0,
        steps=[BlueprintStep(name="s1", description="d1", system="sys1", requires_approval=False)]
    )
    assert validate_hitl_blueprint(schema, RiskDecision.HUMAN_IN_THE_LOOP) == False

def test_safe_blueprint_no_approval_needed():
    schema = BlueprintSchema(
        trigger="test",
        estimated_savings_hours=1.0,
        steps=[BlueprintStep(name="s1", description="d1", system="sys1", requires_approval=False)]
    )
    assert validate_hitl_blueprint(schema, RiskDecision.PRE_APPROVED) == True
