import asyncio
import time
import uuid
import traceback
from datetime import datetime
from typing import Any, Type

from pydantic import BaseModel
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler
from typing_extensions import Never

from agents_config import build_agents
from schemas import (
    ProblemStructuringOutput,
    StrategicAnalysisOutput,
    ReportOutput,
    GovernanceOutput,
)
from retrieval import build_retrieval_query, retrieve_external_context_raw
from logging_utils import save_full_run, append_metrics_row


def format_evidence_bundle(retrieval_data: dict) -> str:
    if not retrieval_data or not retrieval_data.get("documents"):
        return "No external evidence available."

    lines = []
    for doc in retrieval_data["documents"]:
        lines.append(
            f"""[{doc.get('evidence_id', '')}]
Title: {doc.get('title', '')}
Source: {doc.get('source_domain', '')}
Link: {doc.get('link', '')}
Snippet: {doc.get('snippet', '')}
Content Extract: {doc.get('content', '')[:1500]}
Relevance Score: {doc.get('relevance_score', 0.0)}
"""
        )
    return "\n".join(lines)


def extract_usage(response: Any) -> dict:
    """
    Best-effort usage extraction for Agent Framework AgentResponse.
    """
    usage = {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
    }

    candidates = [
        getattr(response, "usage_details", None),
        getattr(response, "usage", None),
        getattr(response, "metadata", None),
        getattr(getattr(response, "raw_response", None), "usage", None),
    ]

    for candidate in candidates:
        if not candidate:
            continue

        if isinstance(candidate, dict):
            usage["input_tokens"] = (
                candidate.get("input_tokens")
                or candidate.get("prompt_tokens")
                or candidate.get("input_token_count")
            )
            usage["output_tokens"] = (
                candidate.get("output_tokens")
                or candidate.get("completion_tokens")
                or candidate.get("output_token_count")
            )
            usage["total_tokens"] = (
                candidate.get("total_tokens")
                or candidate.get("total_token_count")
            )

            if any(v is not None for v in usage.values()):
                return usage

        for src, dst in [
            ("input_tokens", "input_tokens"),
            ("prompt_tokens", "input_tokens"),
            ("input_token_count", "input_tokens"),
            ("output_tokens", "output_tokens"),
            ("completion_tokens", "output_tokens"),
            ("output_token_count", "output_tokens"),
            ("total_tokens", "total_tokens"),
            ("total_token_count", "total_tokens"),
        ]:
            value = getattr(candidate, src, None)
            if value is not None:
                usage[dst] = value

        if any(v is not None for v in usage.values()):
            return usage

    return usage

def estimate_cost_usd(input_tokens: int | None, output_tokens: int | None) -> float | None:
    """
    Estimated cost for Azure OpenAI deployment.
    Update these rates to match your actual deployed model pricing.
    Rates below are placeholders per 1M tokens.
    """
    if input_tokens is None or output_tokens is None:
        return None

    INPUT_PRICE_PER_1M = 0.38   #GPT-4.1-mini-2025-04-14 Regional
    OUTPUT_PRICE_PER_1M = 1.50  

    cost = (input_tokens / 1_000_000) * INPUT_PRICE_PER_1M + (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M
    return round(cost, 6)


import json
from pydantic import ValidationError

async def run_structured_agent(
    agent,
    prompt: str,
    response_model: Type[BaseModel],
) -> tuple[BaseModel, dict]:
    response = await agent.run(
        prompt,
        response_format=response_model,
        temperature=0,
    )

    usage = extract_usage(response)

    # Best case: Agent Framework already parsed it for us
    if getattr(response, "value", None) is not None:
        return response.value, usage

    # Fallback 1: use response.text if available
    raw_text = getattr(response, "text", None)

    # Fallback 2: extract text from messages
    if not raw_text:
        messages = getattr(response, "messages", None) or []
        text_parts = []
        for msg in messages:
            msg_text = getattr(msg, "text", None)
            if msg_text:
                text_parts.append(msg_text)
        if text_parts:
            raw_text = "\n".join(text_parts)

    # Fallback 3: try raw representation if present
    if not raw_text:
        raw_repr = getattr(response, "raw_representation", None)
        if raw_repr:
            raw_text = str(raw_repr)

    if not raw_text:
        raise ValueError(
            f"Structured output was not returned by the agent and no raw text was available. "
            f"Response type: {type(response)}"
        )

    # Remove markdown fences if model wrapped the JSON
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    # Try JSON -> Pydantic
    try:
        data = json.loads(cleaned)
        parsed = response_model.model_validate(data)
        return parsed, usage
    except (json.JSONDecodeError, ValidationError) as ex:
        raise ValueError(
            f"Structured output was not returned by the agent in a parseable form.\n"
            f"Response model: {response_model.__name__}\n"
            f"Raw text:\n{raw_text}\n\n"
            f"Parse error: {ex}"
        ) from ex


class ProblemStructuringExecutor(Executor):
    def __init__(self, agents: dict[str, Any], id: str = "problem_structuring"):
        super().__init__(id=id)
        self.agent = agents["problem_structuring"]

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[dict]) -> None:
        prompt = f"""
Case description:
{payload["case_description"]}

Return a JSON object with EXACTLY these fields:
- company_analysis: string
- market_analysis: string
- key_challenges: list of strings
- areas_of_improvement: list of strings
- kpis: list of strings
- strategic_questions: list of strings

Rules:
- Return ONLY valid JSON.
- Do NOT include markdown fences.
- Do NOT include explanatory text before or after the JSON.
- Do NOT omit any field.
- Use empty lists [] if needed.
- Focus only on diagnosis, not recommendations.

Return JSON only.
""".strip()

        start = time.time()
        parsed, usage = await run_structured_agent(
            self.agent,
            prompt,
            ProblemStructuringOutput,
        )

        payload["problem_structuring_output"] = parsed.model_dump()
        payload["agents"]["agent_1"] = {
            "latency": round(time.time() - start, 4),
            "tokens": usage.get("total_tokens"),
            "cost": estimate_cost_usd(
                usage.get("input_tokens"),
                usage.get("output_tokens"),
            ),
            "valid_output": True,
        }

        await ctx.send_message(payload)


class RetrievalExecutor(Executor):
    def __init__(self, use_external_rag: bool = True, id: str = "retrieval"):
        super().__init__(id=id)
        self.use_external_rag = use_external_rag

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[dict]) -> None:
        start = time.time()

        retrieval_data = {
            "query": "",
            "documents": [],
            "cache_hit": False,
            "retrieval_latency": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.use_external_rag:
            query = build_retrieval_query(payload["problem_structuring_output"])
            retrieval_data = retrieve_external_context_raw(query)

        payload["retrieval"] = retrieval_data
        
        SERPER_COST_PER_QUERY = 0.00087 # $1.00/1k

        payload["agents"]["retrieval"] = {
            "latency": round(time.time() - start, 4),
            "tokens": 0,
            "cost": SERPER_COST_PER_QUERY if self.use_external_rag else 0,
            "valid_output": True,
        }

        await ctx.send_message(payload)


class StrategicAnalysisExecutor(Executor):
    def __init__(self, agents: dict[str, Any], id: str = "strategic_analysis"):
        super().__init__(id=id)
        self.agent = agents["strategic_analysis"]

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[dict]) -> None:
        evidence_bundle = format_evidence_bundle(payload.get("retrieval", {}))

        prompt = f"""
Case description:
{payload["case_description"]}

Problem Structuring Output:
{payload["problem_structuring_output"]}

External Evidence:
{evidence_bundle}

Return a JSON object with EXACTLY these fields:
- strategic_alternatives: list of objects, where each object has:
  - id: string
  - title: string
  - strategic_rationale: string
  - expected_impact_summary: string
  - risk_summary: string
  - priority_score: float or null
  - evidence_ids: list of strings
- trade_off_analysis: string
- prioritization_logic: string
- recommended_option: string

Rules:
- Return ONLY valid JSON.
- Do NOT include markdown fences.
- Do NOT include explanatory text before or after the JSON.
- Do NOT omit any field.
- Use empty lists [] if needed.
- Generate 3 to 5 strategic alternatives.
- Ground alternatives in the provided evidence.
- Use evidence_ids explicitly when external evidence supports a claim.
- Do not state external facts unless supported by the evidence above.

Return JSON only.
""".strip()

        start = time.time()
        parsed, usage = await run_structured_agent(
            self.agent,
            prompt,
            StrategicAnalysisOutput,
        )

        payload["strategic_analysis_output"] = parsed.model_dump()
        payload["agents"]["agent_2"] = {
            "latency": round(time.time() - start, 4),
            "tokens": usage.get("total_tokens"),
            "cost": estimate_cost_usd(
                usage.get("input_tokens"),
                usage.get("output_tokens"),
            ),
            "valid_output": True,
        }

        await ctx.send_message(payload)


class ReportGenerationExecutor(Executor):
    def __init__(self, agents: dict[str, Any], id: str = "report_generation"):
        super().__init__(id=id)
        self.agent = agents["report_generation"]

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[dict]) -> None:
        prompt = f"""
Problem Structuring Output:
{payload["problem_structuring_output"]}

Strategic Analysis Output:
{payload["strategic_analysis_output"]}

Retrieved Evidence:
{payload.get("retrieval", {}).get("documents", [])}

Return a JSON object with EXACTLY these fields:

- executive_summary: string
- key_insights: list of 3 to 5 concise strings
- company_and_market_overview: string
- strategic_alternatives_section: list of 3 to 5 objects, where each object has:
  - id: string
  - title: string
  - strategic_rationale: string
  - expected_impact_summary: string
  - risk_summary: string
  - evidence_ids: list of strings
  - apa_citations: list of strings
- trade_off_discussion: string
- financial_impact_summary: list of objects, where each object has:
  - metric: string
  - estimate: string
  - rationale: string
  - apa_citations: list of strings
- final_recommendation: object with:
  - selected_alternative: string
  - justification: string
  - implementation_roadmap_summary: string
  - evidence_ids: list of strings
  - apa_citations: list of strings
- implementation_timeline: list of objects, where each object has:
  - phase_title: string
  - timeline: string
  - objectives: list of strings
  - key_actions: list of strings
  - expected_outputs: list of strings
- risks_and_mitigation: list of objects, where each object has:
  - risk: string
  - mitigation: string
  - severity: string
  - apa_citations: list of strings
- conclusion: string
- references: list of strings

Rules:
- Return ONLY valid JSON.
- Do NOT include markdown fences.
- Do NOT include explanatory text before or after the JSON.
- Do NOT omit any field.
- Use empty lists [] if needed.
- Write in a professional strategic consulting style, not in an AI assistant tone.
- Be direct, analytical, and decision-oriented.
- Avoid phrases like "this report will analyze", "AI-generated", "the model suggests", or similar.
- Keep the report rich enough to support a final DOCX of around 8 to 10 pages.
- Include exactly 3 to 5 strategic alternatives, not fewer and not more.
- Preserve rankings and numerical estimates exactly where already available.
- Add quantified impact wherever possible, including margin improvement, cost reduction, payback logic, operational effects, or customer outcomes.
- Include APA-style in-text citations in prose using formats like:
  - (Savills, 2024)
  - (McKinsey & Company, 2023)
  - (Retail Trends, n.d.)
- Use source organization/title/domain from the retrieved evidence to construct citations when full author data is unavailable.
- Do NOT show placeholder evidence labels such as E1, E2, E7 in the final prose.
- Use the apa_citations fields to store the citation strings used for each section.
- Include a final references list in APA-style text form.
- The implementation timeline must be phased and specific, for example 0-3 months, 3-9 months, 9-18 months.
- The risks_and_mitigation section must be practical and managerial, not generic.
- The financial_impact_summary must be concise, quantified, and executive-friendly.

Return JSON only.
""".strip()

        start = time.time()
        parsed, usage = await run_structured_agent(
            self.agent,
            prompt,
            ReportOutput,
        )

        payload["report"] = parsed.model_dump()
        payload["agents"]["agent_3"] = {
            "latency": round(time.time() - start, 4),
            "tokens": usage.get("total_tokens"),
            "cost": estimate_cost_usd(
                usage.get("input_tokens"),
                usage.get("output_tokens"),
            ),
            "valid_output": True,
        }

        await ctx.send_message(payload)


class GovernanceExecutor(Executor):
    def __init__(self, agents: dict[str, Any], id: str = "governance"):
        super().__init__(id=id)
        self.agent = agents["governance"]

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[Never, dict]) -> None:
        prompt = f"""
Problem Structuring Output:
{payload["problem_structuring_output"]}

Strategic Analysis Output:
{payload["strategic_analysis_output"]}

Report Output:
{payload["report"]}

External Evidence:
{format_evidence_bundle(payload.get("retrieval", {}))}

Return a JSON object with EXACTLY these fields:
- structural_validation: object with:
  - schema_compliance_score: float
  - missing_fields: list of strings
  - formatting_issues_detected: boolean
- cross_agent_consistency: object with:
  - numerical_consistency_score: float
  - inconsistencies_found: list of strings
- logical_coherence: object with:
  - strategy_alignment_score: float
  - diagnosis_alignment_score: float
  - justification_consistency_score: float
- risk_evaluation: object with:
  - risk_realism_score: float
  - confidence_calibration_score: float
- governance_flags: object with:
  - hallucination_detected: boolean
  - unsupported_claims: list of strings
  - overconfidence_detected: boolean
- overall_governance_score: float

Rules:
- Return ONLY valid JSON.
- Do NOT include markdown fences.
- Do NOT include explanatory text before or after the JSON.
- Do NOT omit any field.
- Use empty lists [] if needed.
- Be strict and conservative in scoring.
- Scores should be between 0 and 10.
- Check whether evidence_ids are present where needed.
- Flag unsupported claims when evidence is missing.

Return JSON only.
""".strip()

        start = time.time()
        parsed, usage = await run_structured_agent(
            self.agent,
            prompt,
            GovernanceOutput,
        )

        governance_output = parsed.model_dump()
        payload["governance_output"] = governance_output
        payload["agents"]["agent_4"] = {
            "latency": round(time.time() - start, 4),
            "tokens": usage.get("total_tokens"),
            "cost": estimate_cost_usd(
                usage.get("input_tokens"),
                usage.get("output_tokens"),
            ),
            "valid_output": True,
        }

        score = governance_output.get("overall_governance_score", 0.0)
        hallucination = governance_output.get("governance_flags", {}).get("hallucination_detected", False)

        total_tokens = 0
        total_cost = 0.0
        has_any_tokens = False
        has_any_cost = False

        for agent_name, meta in payload["agents"].items():
            tokens = meta.get("tokens")
            cost = meta.get("cost")

            if isinstance(tokens, int):
                total_tokens += tokens
                has_any_tokens = True

            if isinstance(cost, (int, float)):
                total_cost += float(cost)
                has_any_cost = True

        payload["metrics"] = {
            "total_tokens": total_tokens if has_any_tokens else None,
            "total_cost_usd": round(total_cost, 6) if has_any_cost else None,
            "governance_score": score,
            "hallucination_detected": hallucination,
        }

        payload["delivery_status"] = (
            "approved_for_export"
            if score >= 8.0 and not hallucination
            else "internal_review_required"
        )

        await ctx.yield_output(payload)


def create_workflow(use_external_rag: bool = True):
    agents = build_agents()

    step_1 = ProblemStructuringExecutor(agents)
    step_2 = RetrievalExecutor(use_external_rag=use_external_rag)
    step_3 = StrategicAnalysisExecutor(agents)
    step_4 = ReportGenerationExecutor(agents)
    step_5 = GovernanceExecutor(agents)

    workflow = (
        WorkflowBuilder(start_executor=step_1)
        .add_edge(step_1, step_2)
        .add_edge(step_2, step_3)
        .add_edge(step_3, step_4)
        .add_edge(step_4, step_5)
        .build()
    )
    return workflow


class ConsultingWorkflow:
    def __init__(self, architecture: str = "multi_agent_4_microsoft_v2", use_external_rag: bool = True):
        self.architecture = architecture
        self.use_external_rag = use_external_rag

    async def run_async(self, case_description: str, case_id: str | None = None) -> dict:
        run_id = str(uuid.uuid4())
        case_id = case_id or str(uuid.uuid4())

        run_record = {
            "run_id": run_id,
            "case_id": case_id,
            "architecture": self.architecture,
            "use_external_rag": self.use_external_rag,
            "success": True,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "latency_seconds": {},
            "agents": {},
            "problem_structuring_output": None,
            "retrieval": None,
            "strategic_analysis_output": None,
            "report": None,
            "governance_output": None,
            "metrics": {},
            "delivery_status": None,
            "case_description": case_description,
        }

        total_start = time.time()

        try:
            workflow = create_workflow(use_external_rag=self.use_external_rag)
            events = await workflow.run(run_record)
            outputs = events.get_outputs()

            if not outputs:
                raise RuntimeError("Workflow completed without outputs.")

            final_payload = outputs[-1]
            run_record.update(final_payload)
            run_record["latency_seconds"]["total"] = round(time.time() - total_start, 4)

        except Exception:
            run_record["success"] = False
            run_record["error"] = traceback.format_exc()
            run_record["latency_seconds"]["total"] = round(time.time() - total_start, 4)

        try:
            save_full_run(run_record)
        except Exception:
            pass

        try:
            append_metrics_row(run_record)
        except Exception:
            pass

        return run_record

    def run(self, case_description: str, case_id: str | None = None) -> dict:
        return asyncio.run(self.run_async(case_description, case_id))