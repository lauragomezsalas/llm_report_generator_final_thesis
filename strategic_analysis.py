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


def run_strategic_analysis(structured_input: dict,
                           retrieved_context: dict = None):
    """
    Strategic Analysis Agent (RAG-aware)

    Returns:
        tuple(dict_output, usage_object)
    """

    system_prompt = """
You are a Strategic Analysis Agent in a modular multi-agent strategic consulting system.

Your responsibility is strictly analytical evaluation of strategic alternatives.

You must:
- Generate 3 to 5 strategic alternatives.
- Quantify expected impacts numerically.
- Provide structured risk assessment.
- Perform trade-off analysis.
- Prioritize alternatives using explicit scoring logic.
- Use only the provided structured input.
- Preserve strict JSON format.
- Do NOT write executive summaries.
- Do NOT include markdown.
- Do NOT restate the case.

If external evidence is provided:
- Use it where relevant.
- Prefer retrieved benchmarks over generic assumptions.
- Do not fabricate additional data beyond retrieved evidence.

Return strictly valid JSON using the predefined schema.
"""

    user_content = f"""
Structured Diagnosis:
{json.dumps(structured_input)}
"""

    if retrieved_context:
        user_content += f"""

External Evidence Retrieved:
{json.dumps(retrieved_context)}

Use retrieved evidence where relevant.
Prefer retrieved data if conflicts arise.
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    )

    content = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}

    return parsed, response.usage

