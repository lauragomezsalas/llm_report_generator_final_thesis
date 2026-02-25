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


def run_problem_structuring(case_description: str) -> dict:

    system_prompt = """
You are a senior retail strategy consultant.

Your task is to:

1. Analyze the company situation.
2. Analyze the market context.
3. Identify key challenges.
4. Identify areas of improvement.
5. Define relevant KPIs.
6. Formulate strategic questions.

You MUST return valid JSON only.
No explanations.
No markdown.
No extra text.

JSON format:

{
  "company_analysis": "...",
  "market_analysis": "...",
  "key_challenges": [],
  "areas_of_improvement": [],
  "kpis": [],
  "strategic_questions": []
}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": case_description}
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content), response.usage
    except json.JSONDecodeError:
        print("⚠️ JSON parsing failed. Raw output:")
        print(content)
        return {}
