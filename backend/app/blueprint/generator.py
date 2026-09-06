import json
import logging
import httpx
from app.blueprint.preconditions import check_blueprint_allowed
from app.blueprint.schema import BlueprintSchema, validate_hitl_blueprint
from app.constants import RiskDecision
from app.config import Settings

logger = logging.getLogger(__name__)

class BlueprintGenerationError(Exception):
    pass

async def generate_blueprint(process_name: str, process_description: str, systems: list[str], risk_decision: RiskDecision, settings: Settings) -> BlueprintSchema:
    # Hard gate
    check_blueprint_allowed(risk_decision)
    
    if not settings.GROQ_API_KEY:
        raise BlueprintGenerationError("GROQ_API_KEY is not configured.")
        
    prompt = f"""
    Generate an automation blueprint for the process '{process_name}'.
    Description: {process_description}
    Systems: {', '.join(systems)}
    Risk Decision: {risk_decision.value}
    
    Respond ONLY with a valid JSON object matching this schema:
    {{
        "trigger": "string",
        "estimated_savings_hours": float,
        "steps": [
            {{
                "name": "string",
                "description": "string",
                "system": "string",
                "requires_approval": boolean,
                "approval_condition": "string or null"
            }}
        ]
    }}
    """
    
    if risk_decision == RiskDecision.HUMAN_IN_THE_LOOP:
        prompt += "\nAt least one step MUST have requires_approval = true."
        
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a senior automation architect. You design robust, enterprise-grade automation blueprints."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }
    
    for attempt in range(3):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                blueprint_data = json.loads(content)
                blueprint = BlueprintSchema.model_validate(blueprint_data)
                
                if validate_hitl_blueprint(blueprint, risk_decision):
                    return blueprint
                else:
                    logger.warning(f"Attempt {attempt + 1}: HITL validation failed. Retrying...")
                    prompt += "\nREMINDER: You failed to include a step with requires_approval = true. Fix this."
                    payload["messages"][1]["content"] = prompt
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            
    raise BlueprintGenerationError("Failed to generate a valid blueprint after 3 attempts.")
