import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

MODEL_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def run_governance_evaluation(problem_structuring_output: dict,
                              strategic_analysis_output: dict,
                              report_output: dict) -> dict:
    """
    Governance & Critique Agent

    Input:
        problem_structuring_output (dict)
        strategic_analysis_output (dict)
        report_output (dict)

    Output:
        dict -> Governance evaluation JSON
    """

    system_prompt = """
You are a Governance and Audit Agent in a modular multi-agent strategic consulting system.

Your task is to evaluate the outputs of previous agents.

You must:
- Detect structural violations.
- Check cross-agent numerical consistency.
- Evaluate logical coherence between diagnosis, analysis, and report.
- Detect hallucinations or unsupported claims.
- Evaluate realism of risk and impact estimates.
- Score each dimension between 0 and 10.
- Return valid JSON only.
- Do NOT rewrite the report.
- Do NOT improve the strategy.
- Do NOT provide recommendations.
- Do NOT include explanations outside JSON.
- Do NOT use markdown.

Scoring rules:
0 = completely invalid
5 = acceptable but flawed
10 = fully consistent, realistic, and coherent

Be strict and conservative in scoring.

Return strictly valid JSON using this schema:

{
  "structural_validation": {
    "schema_compliance_score": 0,
    "missing_fields": [],
    "formatting_issues_detected": false
  },
  "cross_agent_consistency": {
    "numerical_consistency_score": 0,
    "inconsistencies_found": []
  },
  "logical_coherence": {
    "strategy_alignment_score": 0,
    "diagnosis_alignment_score": 0,
    "justification_consistency_score": 0
  },
  "risk_evaluation": {
    "risk_realism_score": 0,
    "confidence_calibration_score": 0
  },
  "governance_flags": {
    "hallucination_detected": false,
    "unsupported_claims": [],
    "overconfidence_detected": false
  },
  "overall_governance_score": 0
}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""
Problem Structuring Output:
{json.dumps(problem_structuring_output)}

Strategic Analysis Output:
{json.dumps(strategic_analysis_output)}

Report Output:
{json.dumps(report_output)}

Evaluate the system outputs and return the governance JSON.
"""
            }
        ]
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content), response.usage
    except json.JSONDecodeError:
        return {}
