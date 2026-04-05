import json
from typing import Any

from config import (
    build_governance_client,
    GOVERNANCE_AZURE_OPENAI_DEPLOYMENT_NAME,
)
from schemas import GovernanceOutput


def build_clean_governance_messages(
    consultant_brief: dict,
    report_output: dict,
    external_evidence: dict,
) -> list[dict[str, Any]]:
    system_prompt = """
You are an independent audit evaluator for strategic consulting reports.

IMPORTANT INSTRUCTIONS:
- You are NOT part of the report generation pipeline.
- You must evaluate the report independently and critically.
- You must NOT assume the report is correct.
- You must use ONLY:
  1) the consultant brief,
  2) the final report,
  3) the retrieved evidence bundle.
- You must NOT infer quality from hidden prior reasoning or internal chain outputs.
- Be conservative and skeptical.
- All scores MUST be on a 0-10 scale.
- Score meanings:
  0-2 = very poor
  3-4 = weak
  5-6 = acceptable
  7-8 = strong
  9 = excellent
  10 = exceptional and extremely rare
- If the report contains generic business advice not clearly grounded in evidence, reduce scores.
- If a recommendation is weakly justified, reduce justification_consistency_score.
- If claims are unsupported by evidence, list them in unsupported_claims.
- overall_governance_score should reflect weaknesses and should not exceed the weakest major dimension by a large margin.

Return ONLY valid JSON matching this schema:
{
  "structural_validation": {
    "schema_compliance_score": float,
    "missing_fields": [str],
    "formatting_issues_detected": bool
  },
  "cross_agent_consistency": {
    "numerical_consistency_score": float,
    "inconsistencies_found": [str]
  },
  "logical_coherence": {
    "strategy_alignment_score": float,
    "diagnosis_alignment_score": float,
    "justification_consistency_score": float
  },
  "risk_evaluation": {
    "risk_realism_score": float,
    "confidence_calibration_score": float
  },
  "governance_flags": {
    "hallucination_detected": bool,
    "unsupported_claims": [str],
    "overconfidence_detected": bool
  },
  "overall_governance_score": float
}
""".strip()

    user_prompt = f"""
CONSULTANT BRIEF:
{json.dumps(consultant_brief, ensure_ascii=False, indent=2)}

FINAL REPORT TO AUDIT:
{json.dumps(report_output, ensure_ascii=False, indent=2)}

RETRIEVED EVIDENCE:
{json.dumps(external_evidence, ensure_ascii=False, indent=2)}
""".strip()

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def clean_json_text(raw_text: str) -> str:
    cleaned = raw_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned


def run_clean_governance(
    consultant_brief: dict,
    report_output: dict,
    external_evidence: dict,
) -> tuple[dict, dict]:
    client = build_governance_client()
    messages = build_clean_governance_messages(
        consultant_brief=consultant_brief,
        report_output=report_output,
        external_evidence=external_evidence,
    )

    response = client.chat.completions.create(
        model=GOVERNANCE_AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=messages,
        temperature=0,
    )

    raw_text = response.choices[0].message.content or ""
    cleaned = clean_json_text(raw_text)
    parsed = GovernanceOutput.model_validate(json.loads(cleaned))

    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
    total_tokens = getattr(usage, "total_tokens", None) if usage else None

    return parsed.model_dump(), {
        "tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "raw_output_preview": cleaned[:500],
    }