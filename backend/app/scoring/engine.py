import math

def compute_value_score(factors: dict[str, float], weights: dict[str, float]) -> float:
    # Validate keys match
    if set(factors.keys()) != set(weights.keys()):
        raise ValueError("Keys in factors and weights must match perfectly.")
    
    # Validate weights sum
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=0.001):
        raise ValueError("Weights must sum to approximately 1.0")
        
    score = sum(factors[k] * weights[k] for k in factors)
    score = max(0.0, min(100.0, score))
    return round(score, 1)
