"""Semantic analysis of a discovered process.

Groq supplies *qualitative interpretation* — what the process is, which systems
it touches, whether it looks rule-based. It never decides the final score, and
critically it can never make a process look safer than deterministic policy
says it is.

The safety rule implemented here:

    sensitive_outcome = policy_says_sensitive OR llm_says_sensitive
    fully_rule_based  = policy_says_rule_based AND llm_says_rule_based

Both combinations are one-directional. A hallucinating, prompt-injected or
simply wrong model can only ever move a process *toward* more human oversight,
never away from it. That is what keeps the risk gate trustworthy while still
letting an LLM do the interpretation work.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional, Sequence

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Deterministic sensitivity policy. If any of these appear in a process's
# activity text, the process is sensitive REGARDLESS of what the model says.
# Editable by a human, versioned in code, auditable — unlike a model opinion.
SENSITIVE_PATTERNS = (
    r"payroll", r"\btax\b", r"remitt", r"salary", r"compensation",
    r"terminat", r"dismiss", r"redundan", r"disciplin", r"grievance",
    r"medical", r"health record", r"patient", r"diagnos",
    r"legal", r"litigat", r"contract award", r"regulatory filing",
    r"ledger reconcil", r"wire transfer", r"fund transfer", r"settlement",
    r"credit decision", r"loan approv", r"background check", r"visa\b",
)

# Wording that indicates human judgement rather than a deterministic rule.
JUDGEMENT_PATTERNS = (
    r"review", r"assess", r"evaluat", r"approv", r"negotiat", r"investigat",
    r"decide", r"judg", r"discretion", r"exception handling", r"escalat",
)


class SemanticAnalysis(BaseModel):
    """Structured interpretation of a process. Mirrors the agreed contract."""

    canonical_process_name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=800)
    automation_candidate: bool = True
    systems_involved: list[str] = Field(default_factory=list)
    human_judgment_required: bool = True
    rule_based: bool = False
    sensitive_outcome: bool = True
    reasoning: str = Field(default="", max_length=800)
    # 0-100, how deterministic the steps look. Feeds rule_determinism.
    determinism_score: float = Field(default=50.0, ge=0.0, le=100.0)


@dataclass
class PolicySignals:
    """What deterministic policy concludes, independent of any model."""

    sensitive: bool
    sensitive_reason: Optional[str]
    judgement_required: bool


def apply_policy(activities: Sequence[str], process_name: str = "") -> PolicySignals:
    """Deterministic, keyword-driven risk signals.

    Runs whether or not an LLM is available, and its verdict is never
    overridden by one.
    """
    haystack = " ".join([process_name, *activities]).lower()

    hit = next(
        (p for p in SENSITIVE_PATTERNS if re.search(p, haystack)),
        None,
    )
    judgement = any(re.search(p, haystack) for p in JUDGEMENT_PATTERNS)

    return PolicySignals(
        sensitive=hit is not None,
        sensitive_reason=(
            f"matched sensitive-domain policy pattern '{hit}'" if hit else None
        ),
        judgement_required=judgement,
    )


def _heuristic_analysis(
    fallback_name: str, activities: Sequence[str], systems: Sequence[str]
) -> SemanticAnalysis:
    """Used when Groq is unavailable. Deliberately conservative: without a
    model to interpret the work, we assume judgement is required rather than
    assuming the process is safe."""
    policy = apply_policy(activities, fallback_name)
    return SemanticAnalysis(
        canonical_process_name=fallback_name,
        description="Derived without semantic analysis (LLM unavailable).",
        automation_candidate=not policy.sensitive,
        systems_involved=list(systems),
        human_judgment_required=policy.judgement_required or policy.sensitive,
        rule_based=not policy.judgement_required and not policy.sensitive,
        sensitive_outcome=policy.sensitive,
        reasoning=policy.sensitive_reason or "No sensitive policy pattern matched.",
        determinism_score=40.0 if policy.judgement_required else 70.0,
    )


_PROMPT = """You are analysing a repetitive business process discovered from a work event log.

Cluster label: {name}
Observed activities:
{activities}
Systems seen in the log: {systems}
Cases observed: {cases} | Average handling time: {minutes} minutes | Rework rate: {rework:.0%}

Return ONLY a JSON object with exactly these keys:
{{
  "canonical_process_name": "a clear business name for this process",
  "description": "one or two sentences describing what the work involves",
  "automation_candidate": true or false,
  "systems_involved": ["..."],
  "human_judgment_required": true or false,
  "rule_based": true or false,
  "sensitive_outcome": true or false,
  "reasoning": "why you reached these conclusions",
  "determinism_score": 0-100
}}

Guidance:
- "rule_based" means every step follows a deterministic rule with no discretion.
- "sensitive_outcome" means the outcome has legal, financial, medical or
  employment consequences for a person or the organisation.
- "determinism_score" is how mechanical the steps are (100 = fully mechanical).
Be conservative: if unsure, prefer human_judgment_required = true."""


async def analyse_process(
    *,
    cluster_name: str,
    activities: Sequence[str],
    systems: Sequence[str],
    cases: int,
    avg_minutes: float,
    rework_rate: float,
    settings: Settings,
    timeout: float = 30.0,
) -> SemanticAnalysis:
    """Interpret a process, then harden the result against policy.

    Always returns a usable analysis — if Groq is missing, misbehaving or
    returns malformed JSON, the deterministic heuristic is used instead.
    """
    analysis: Optional[SemanticAnalysis] = None

    if settings.GROQ_API_KEY:
        prompt = _PROMPT.format(
            name=cluster_name,
            activities="\n".join(f"- {a}" for a in activities) or "- (none)",
            systems=", ".join(systems) or "unknown",
            cases=cases,
            minutes=round(avg_minutes, 1),
            rework=rework_rate,
        )
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a process-mining analyst. You classify business "
                        "processes precisely and conservatively. Reply with JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    GROQ_URL, headers=headers, json=payload, timeout=timeout
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                analysis = SemanticAnalysis.model_validate(json.loads(content))
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError) as exc:
            # A failed interpretation must never fail the pipeline — it falls
            # back to the conservative heuristic instead.
            logger.warning("Semantic analysis failed for %r: %s", cluster_name, exc)

    if analysis is None:
        analysis = _heuristic_analysis(cluster_name, activities, systems)

    return harden_with_policy(analysis, activities)


def harden_with_policy(
    analysis: SemanticAnalysis, activities: Sequence[str]
) -> SemanticAnalysis:
    """Combine model output with deterministic policy, one-directionally.

    Policy can escalate risk. Neither policy nor the model can reduce it below
    what the other found. This is what makes an LLM safe to use upstream of a
    risk gate.
    """
    policy = apply_policy(activities, analysis.canonical_process_name)

    hardened = analysis.model_copy(deep=True)

    if policy.sensitive and not hardened.sensitive_outcome:
        logger.info(
            "Policy escalated %r to sensitive (%s); model had said otherwise.",
            hardened.canonical_process_name,
            policy.sensitive_reason,
        )
        hardened.reasoning = (
            f"{hardened.reasoning} | Escalated by deterministic policy: "
            f"{policy.sensitive_reason}."
        ).strip(" |")

    # OR for risk, AND for safety — never the other way round.
    hardened.sensitive_outcome = analysis.sensitive_outcome or policy.sensitive
    hardened.rule_based = analysis.rule_based and not policy.judgement_required
    hardened.human_judgment_required = (
        analysis.human_judgment_required or policy.judgement_required
    )
    if hardened.sensitive_outcome:
        hardened.automation_candidate = False

    return hardened
