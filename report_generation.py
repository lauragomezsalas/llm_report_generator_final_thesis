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


def run_report_generation(problem_structuring_output: dict,
                          strategic_analysis_output: dict) -> dict:
    """
    Report Generation Agent

    Input:
        problem_structuring_output (dict)
        strategic_analysis_output (dict)

    Output:
        dict -> Structured executive report JSON
    """

    system_prompt = """
You are a Report Generation Agent in a modular multi-agent strategic consulting system.

Your role is to convert structured strategic analysis into a coherent executive-style report.

You must:
- Use only the provided structured inputs.
- Preserve all numerical values exactly as given.
- Preserve prioritization order.
- Not introduce new strategic alternatives.
- Not modify impact estimates.
- Not perform additional analysis.
- Not critique governance.
- Not add assumptions not present in the inputs.
- Return valid JSON only.
- Do not use markdown.
- Do not include explanations outside JSON.

Return strictly valid JSON using this schema:

{
  "executive_summary": "",
  "company_and_market_overview": "",
  "strategic_alternatives_section": [
    {
      "id": "",
      "title": "",
      "strategic_rationale": "",
      "expected_impact_summary": "",
      "risk_summary": ""
    }
  ],
  "trade_off_discussion": "",
  "final_recommendation": {
    "selected_alternative": "",
    "justification": "",
    "implementation_roadmap_summary": ""
  }
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

Generate the structured executive report JSON.
"""
            }
        ]
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content), response.usage
    except json.JSONDecodeError:
        return {}
