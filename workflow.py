import asyncio
import json
import time
import uuid
import traceback
from datetime import datetime
import dspy
import litellm
import tiktoken
from governance_clean import run_clean_governance

from pydantic import BaseModel, ValidationError
from typing import Any
from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler
from typing_extensions import Never

from schemas import (
    ConsultantBrief,
    IntakeAssessment,
    ProblemStructuringOutput,
    StrategicAnalysisOutput,
    ReportOutput,
    GovernanceOutput,
)
from retrieval import build_retrieval_query, retrieve_external_context_raw
from intake import assess_brief

from logging_utils import save_full_run, append_metrics_row, save_run_to_sqlite
from dspy_modules import (
    ProblemStructuringModule,
    StrategicAnalysisModule,
    ReportGenerationModule,
)

from evaluation_primary import compute_primary_evaluation_metrics

from experiment_config import (
    WORKFLOW_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    INTAKE_VERSION,
    RETRIEVAL_VERSION,
    GOVERNANCE_VERSION,
    MODEL_PROVIDER,
    MODEL_DEPLOYMENT,
    MODEL_API_VERSION,
    MODEL_TEMPERATURE,
    DSPY_TRACK_USAGE,
    GOVERNANCE_APPROVAL_THRESHOLD,
    JSON_RETRY_MAX_RETRIES,
    RETRIEVAL_PROVIDER,
    RETRIEVAL_NUM_RESULTS,
    RETRIEVAL_TOP_K,
    RETRIEVAL_CACHE_ENABLED,
    RETRIEVAL_TIMEOUT_SECONDS,
    PAGE_FETCH_TIMEOUT_SECONDS,
    PAGE_FETCH_MAX_CHARS,
)


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


def estimate_cost_usd(input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None

    INPUT_PRICE_PER_1M = 0.38
    OUTPUT_PRICE_PER_1M = 1.50

    cost = (
        (input_tokens / 1_000_000) * INPUT_PRICE_PER_1M
        + (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M
    )
    return round(cost, 6)


def clean_json_text(raw_text: str) -> str:
    cleaned = raw_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned[len("```"):].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned

def build_schema_example(response_model: type[BaseModel]) -> str:
    """
    Build a recursive JSON skeleton from a Pydantic model to help the model repair output.
    """
    from typing import get_args, get_origin
    from pydantic import BaseModel

    def placeholder_from_annotation(annotation):
        origin = get_origin(annotation)
        args = get_args(annotation)

        if annotation is str:
            return "string"
        if annotation is int:
            return 0
        if annotation is float:
            return 0.0
        if annotation is bool:
            return False

        if origin is list or origin is list:
            if args:
                return [placeholder_from_annotation(args[0])]
            return []

        if origin is dict:
            return {}

        if args:
            # Optional[T], Union[T, None], etc.
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                return placeholder_from_annotation(non_none_args[0])

        try:
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                return {
                    name: placeholder_from_annotation(field.annotation)
                    for name, field in annotation.model_fields.items()
                }
        except Exception:
            pass

        return "value"

    try:
        example = {
            name: placeholder_from_annotation(field.annotation)
            for name, field in response_model.model_fields.items()
        }
        return json.dumps(example, indent=2, ensure_ascii=False)
    except Exception:
        return "{}"


def build_retry_kwargs(
    original_kwargs: dict,
    response_model: type[BaseModel],
    raw_output: str,
    error_message: str,
) -> dict:
    """
    Create retry kwargs by appending a repair instruction to every string input.
    This avoids changing DSPy signatures.
    """
    schema_example = build_schema_example(response_model)

    extra_instruction = ""
    if response_model.__name__ == "ReportOutput":
        extra_instruction = """

    REPORTOUTPUT FIELD RULES:
    - implementation_timeline must be a list of objects with:
    phase_title, timeline, objectives, key_actions, expected_outputs
    - Do NOT use 'phase' or 'description'
    - financial_impact_summary items must contain:
    metric, estimate, rationale, apa_citations
    - Do NOT use 'citation'; use 'apa_citations'
    - strategic_alternatives_section items must include apa_citations
    - final_recommendation must include evidence_ids and apa_citations
    - risks_and_mitigation items must include apa_citations
    """.strip()

    repair_instruction = f"""

IMPORTANT RETRY INSTRUCTION:
Your previous answer was invalid.

You must return ONLY valid JSON with no markdown, no explanation, no code fences.

Target schema: {response_model.__name__}

Schema skeleton:
{schema_example}

{extra_instruction}

Previous invalid output:
{raw_output}

Validation / parsing error:
{error_message}

Return corrected JSON only.
""".strip()

    repaired_kwargs = {}
    for key, value in original_kwargs.items():
        if isinstance(value, str):
            repaired_kwargs[key] = value + "\n\n" + repair_instruction
        else:
            repaired_kwargs[key] = value

    return repaired_kwargs

def build_configuration_snapshot(
    architecture: str,
    use_external_rag: bool,
) -> dict:
    return {
        "versioning": {
            "workflow_version": WORKFLOW_VERSION,
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "intake_version": INTAKE_VERSION,
            "retrieval_version": RETRIEVAL_VERSION,
            "governance_version": GOVERNANCE_VERSION,
        },
        "model": {
            "provider": MODEL_PROVIDER,
            "deployment_name": MODEL_DEPLOYMENT,
            "api_version": MODEL_API_VERSION,
            "temperature": MODEL_TEMPERATURE,
            "track_usage": DSPY_TRACK_USAGE,
        },
        "workflow": {
            "architecture": architecture,
            "use_external_rag": use_external_rag,
            "agent_sequence": [
                "intake",
                "agent_1_problem_structuring",
                "retrieval",
                "agent_2_strategic_analysis",
                "agent_3_report_generation",
                "agent_4_governance",
            ],
        },
        "retrieval": {
            "provider": RETRIEVAL_PROVIDER,
            "num_results": RETRIEVAL_NUM_RESULTS,
            "top_k": RETRIEVAL_TOP_K,
            "cache_enabled": RETRIEVAL_CACHE_ENABLED,
            "request_timeout_seconds": RETRIEVAL_TIMEOUT_SECONDS,
            "page_fetch_timeout_seconds": PAGE_FETCH_TIMEOUT_SECONDS,
            "page_fetch_max_chars": PAGE_FETCH_MAX_CHARS,
        },
        "policy": {
            "governance_approval_threshold": GOVERNANCE_APPROVAL_THRESHOLD,
            "json_retry_max_retries": JSON_RETRY_MAX_RETRIES,
        },
    }

def get_token_encoder(model_name: str | None = None):
    """
    Return a tokenizer encoder. For GPT-4o / GPT-4.1 style models, o200k_base is a good fallback.
    """
    try:
        if model_name:
            try:
                return tiktoken.encoding_for_model(model_name)
            except Exception:
                pass
        return tiktoken.get_encoding("o200k_base")
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


def count_text_tokens(text: str, model_name: str | None = None) -> int:
    if not text:
        return 0
    enc = get_token_encoder(model_name)
    return len(enc.encode(text))


def count_message_tokens(messages: list, model_name: str | None = None) -> int:
    """
    Approximate token count for chat messages by counting each message content plus role text.
    This is not provider-billing exact, but it is the strongest fallback when usage is unavailable.
    """
    if not messages:
        return 0

    total = 0
    for msg in messages:
        if not isinstance(msg, dict):
            total += count_text_tokens(str(msg), model_name)
            continue

        role = str(msg.get("role", ""))
        content = msg.get("content", "")

        total += count_text_tokens(role, model_name)

        if isinstance(content, str):
            total += count_text_tokens(content, model_name)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "text" in item and isinstance(item["text"], str):
                        total += count_text_tokens(item["text"], model_name)
                    else:
                        total += count_text_tokens(json.dumps(item, ensure_ascii=False), model_name)
                else:
                    total += count_text_tokens(str(item), model_name)
        else:
            total += count_text_tokens(str(content), model_name)

    return total


def estimate_tokens_from_history_and_output(
    prediction=None,
    raw_output_text: str | None = None,
    model_name: str | None = None,
) -> dict:
    """
    Fallback token estimation when provider usage is missing.
    Uses the latest DSPy LM history entry plus the model output text.
    """
    prompt_tokens = 0
    completion_tokens = 0

    lm = dspy.settings.lm
    history = getattr(lm, "history", None) if lm is not None else None
    latest = history[-1] if history else None

    if isinstance(latest, dict):
        messages = latest.get("messages")
        prompt = latest.get("prompt")

        if isinstance(messages, list) and messages:
            prompt_tokens = count_message_tokens(messages, model_name)
        elif isinstance(prompt, str) and prompt:
            prompt_tokens = count_text_tokens(prompt, model_name)

    if raw_output_text:
        completion_tokens = count_text_tokens(raw_output_text, model_name)

    total_tokens = prompt_tokens + completion_tokens

    return {
        "tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }

def find_usage_block(obj):
    """
    Safely find a usage block inside a DSPy history entry.
    Supports dicts and lists.
    """
    if isinstance(obj, dict):
        # direct usage
        if isinstance(obj.get("usage"), dict):
            return obj["usage"]

        # nested common keys
        for key in ("response", "outputs", "output", "result"):
            value = obj.get(key)

            if isinstance(value, dict):
                found = find_usage_block(value)
                if found:
                    return found

            if isinstance(value, list):
                for item in reversed(value):
                    found = find_usage_block(item)
                    if found:
                        return found

    elif isinstance(obj, list):
        for item in reversed(obj):
            found = find_usage_block(item)
            if found:
                return found

    return {}


def extract_latest_dspy_usage(
    prediction=None,
    raw_output_text: str | None = None,
    model_name: str | None = None,
) -> dict:
    try:
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        cost = None

        lm = dspy.settings.lm
        resolved_model = model_name or getattr(lm, "model", None)

        # 1) First try prediction._lm_usage
        if prediction is not None:
            lm_usage = getattr(prediction, "_lm_usage", None)

            if isinstance(lm_usage, dict):
                prompt_tokens = lm_usage.get("prompt_tokens")
                completion_tokens = lm_usage.get("completion_tokens")
                total_tokens = lm_usage.get("total_tokens")

            elif hasattr(lm_usage, "__dict__"):
                lm_usage_dict = vars(lm_usage)
                prompt_tokens = lm_usage_dict.get("prompt_tokens")
                completion_tokens = lm_usage_dict.get("completion_tokens")
                total_tokens = lm_usage_dict.get("total_tokens")

        # 2) Fallback to DSPy history
        if prompt_tokens is None and completion_tokens is None and total_tokens is None:
            if lm is not None:
                history = getattr(lm, "history", None)
                if history:
                    latest = history[-1]

                    if isinstance(latest, dict):
                        usage = latest.get("usage") or {}
                        if isinstance(usage, dict):
                            prompt_tokens = usage.get("prompt_tokens")
                            completion_tokens = usage.get("completion_tokens")
                            total_tokens = usage.get("total_tokens")

                        raw_cost = latest.get("cost")
                        if isinstance(raw_cost, (int, float)):
                            cost = float(raw_cost)

        # 3) If still missing, estimate locally from actual prompt/messages + output text
        if prompt_tokens is None and completion_tokens is None and total_tokens is None:
            estimated = estimate_tokens_from_history_and_output(
                prediction=prediction,
                raw_output_text=raw_output_text,
                model_name=resolved_model,
            )
            prompt_tokens = estimated["prompt_tokens"]
            completion_tokens = estimated["completion_tokens"]
            total_tokens = estimated["tokens"]

        # 4) If total still missing but components exist
        if total_tokens is None and (
            prompt_tokens is not None or completion_tokens is not None
        ):
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

        # 5) Estimate cost if needed
        if cost is None and prompt_tokens is not None and completion_tokens is not None:
            # safest path: your explicit pricing function
            cost = estimate_cost_usd(prompt_tokens, completion_tokens)

        return {
            "tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": round(float(cost), 6) if cost is not None else None,
        }

    except Exception:
        return {
            "tokens": None,
            "prompt_tokens": None,
            "completion_tokens": None,
            "cost": None,
        }


async def run_dspy_json(
    module,
    response_model: type[BaseModel],
    max_retries: int = 2,
    **kwargs,
) -> tuple[BaseModel, dict]:
    """
    Run a DSPy module and enforce JSON + schema validation.
    If parsing or validation fails, retry with a repair instruction.
    """
    last_error = None
    attempt_kwargs = dict(kwargs)

    for attempt in range(max_retries + 1):
        prediction = await module.acall(**attempt_kwargs)

        raw_text = getattr(prediction, "json_output", None)

        if not raw_text:
            last_error = ValueError(
                f"DSPy module did not return json_output. "
                f"Module type: {type(module)} | Prediction type: {type(prediction)}"
            )

            if attempt < max_retries:
                attempt_kwargs = build_retry_kwargs(
                    original_kwargs=kwargs,
                    response_model=response_model,
                    raw_output="",
                    error_message=str(last_error),
                )
                continue

            raise last_error

        cleaned = clean_json_text(raw_text)

        try:
            data = json.loads(cleaned)
            parsed = response_model.model_validate(data)

            usage_metrics = extract_latest_dspy_usage(
                prediction=prediction,
                raw_output_text=cleaned,
            )

            usage_metrics["retry_count"] = attempt
            usage_metrics["raw_output_preview"] = cleaned[:500]

            return parsed, usage_metrics

        except (json.JSONDecodeError, ValidationError) as ex:
            last_error = ValueError(
                f"DSPy output could not be parsed into {response_model.__name__}.\n"
                f"Raw output:\n{raw_text}\n\n"
                f"Parse error: {ex}"
            )

            if attempt < max_retries:
                attempt_kwargs = build_retry_kwargs(
                    original_kwargs=kwargs,
                    response_model=response_model,
                    raw_output=raw_text,
                    error_message=str(ex),
                )
                continue

    raise last_error if last_error else RuntimeError("Unknown DSPy JSON parsing failure.")


class ConsultantIntakeExecutor(Executor):
    def __init__(self, id: str = "consultant_intake"):
        super().__init__(id=id)

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[dict]) -> None:
        start = time.time()

        consultant_brief_raw = payload.get("consultant_brief")
        if not consultant_brief_raw:
            raise ValueError("Missing consultant_brief in workflow payload.")

        brief = ConsultantBrief.model_validate(consultant_brief_raw)
        intake = assess_brief(brief)

        payload["consultant_brief"] = brief.model_dump()
        payload["intake_assessment"] = intake.model_dump()
        payload["case_description"] = intake.normalized_case_description

        payload["agents"]["intake"] = {
            "latency": round(time.time() - start, 4),
            "tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost": 0.0,
            "valid_output": intake.is_ready,
        }

        await ctx.send_message(payload)

class ProblemStructuringExecutor(Executor):
    def __init__(self, id: str = "problem_structuring"):
        super().__init__(id=id)
        self.module = ProblemStructuringModule()

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[dict]) -> None:
        start = time.time()

        parsed, usage = await run_dspy_json(
            self.module,
            ProblemStructuringOutput,
            case_description=payload["case_description"],
        )

        payload["problem_structuring_output"] = parsed.model_dump()
        payload["agents"]["agent_1"] = {
            "latency": round(time.time() - start, 4),
            "tokens": usage["tokens"],
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "cost": usage["cost"],
            "retry_count": usage.get("retry_count", 0),
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
            query = build_retrieval_query(
                consultant_brief=payload.get("consultant_brief"),
                problem_structuring_output=payload["problem_structuring_output"],
            )
            retrieval_data = retrieve_external_context_raw(query)

            # Retry once with a shorter fallback query if nothing useful came back
            if not retrieval_data.get("documents"):
                fallback_query = "Spain grocery retail supermarket margins discount retailers supply chain customer loyalty"
                retrieval_data = retrieve_external_context_raw(fallback_query)
                retrieval_data["fallback_query_used"] = fallback_query

            if self.use_external_rag and not retrieval_data.get("documents"):
                raise ValueError(
                    "Retrieval returned no usable documents after retry. Aborting run to avoid unsupported analysis."
                )
        
        payload["retrieval"] = retrieval_data

        SERPER_COST_PER_QUERY = 0.00087

        payload["agents"]["retrieval"] = {
            "latency": round(time.time() - start, 4),
            "tokens": 0,
            "cost": SERPER_COST_PER_QUERY if self.use_external_rag else 0,
            "valid_output": True,
        }

        await ctx.send_message(payload)


class StrategicAnalysisExecutor(Executor):
    def __init__(self, id: str = "strategic_analysis"):
        super().__init__(id=id)
        self.module = StrategicAnalysisModule()

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[dict]) -> None:
        start = time.time()
        evidence_bundle = format_evidence_bundle(payload.get("retrieval", {}))

        parsed, usage = await run_dspy_json(
            self.module,
            StrategicAnalysisOutput,
            case_description=payload["case_description"],
            problem_structuring_output=json.dumps(
                payload["problem_structuring_output"],
                ensure_ascii=False,
                indent=2,
            ),
            external_evidence=evidence_bundle,
        )

        payload["strategic_analysis_output"] = parsed.model_dump()
        payload["agents"]["agent_2"] = {
            "latency": round(time.time() - start, 4),
            "tokens": usage["tokens"],
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "cost": usage["cost"],
            "retry_count": usage.get("retry_count", 0),
            "valid_output": True,
        }

        await ctx.send_message(payload)


class ReportGenerationExecutor(Executor):
    def __init__(self, id: str = "report_generation"):
        super().__init__(id=id)
        self.module = ReportGenerationModule()

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[dict]) -> None:
        start = time.time()
        evidence_bundle = format_evidence_bundle(payload.get("retrieval", {}))

        parsed, usage = await run_dspy_json(
            self.module,
            ReportOutput,
            problem_structuring_output=json.dumps(
                payload["problem_structuring_output"],
                ensure_ascii=False,
                indent=2,
            ),
            strategic_analysis_output=json.dumps(
                payload["strategic_analysis_output"],
                ensure_ascii=False,
                indent=2,
            ),
            external_evidence=evidence_bundle,
        )

        missing = validate_grounding(parsed.model_dump())
        if missing:
            raise ValueError(
                "Report grounding validation failed: " + " | ".join(missing)
            )

        payload["report"] = parsed.model_dump()
        payload["agents"]["agent_3"] = {
            "latency": round(time.time() - start, 4),
            "tokens": usage["tokens"],
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "cost": usage["cost"],
            "retry_count": usage.get("retry_count", 0),
            "valid_output": True,
        }

        await ctx.send_message(payload)

def validate_grounding(report):
    missing = []

    for alt in report.get("strategic_alternatives_section", []):
        if not alt.get("evidence_ids"):
            missing.append(f"Missing evidence_ids in alternative: {alt.get('title')}")

        if not alt.get("apa_citations"):
            missing.append(f"Missing apa_citations in alternative: {alt.get('title')}")

    final_rec = report.get("final_recommendation", {}) or {}
    if not final_rec.get("evidence_ids"):
        missing.append("Missing evidence_ids in final_recommendation")

    if not final_rec.get("apa_citations"):
        missing.append("Missing apa_citations in final_recommendation")

    if not report.get("references"):
        missing.append("Missing references list")

    return missing


class GovernanceExecutor(Executor):
    def __init__(self, id: str = "governance"):
        super().__init__(id=id)

    @handler
    async def handle(self, payload: dict, ctx: WorkflowContext[Never, dict]) -> None:
        start = time.time()

        retrieval_payload = payload.get("retrieval", {}) or {}

        governance_output, usage = run_clean_governance(
            consultant_brief=payload.get("consultant_brief", {}),
            report_output=payload.get("report", {}),
            external_evidence=retrieval_payload,
        )

        payload["governance_output"] = governance_output
        payload["agents"]["agent_4"] = {
            "latency": round(time.time() - start, 4),
            "tokens": usage.get("tokens"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cost": estimate_cost_usd(
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
            ),
            "retry_count": 0,
            "valid_output": True,
            "evaluator_type": "independent_clean_llm",
        }

        # Raw LLM governance score from 0-10 -> normalize to 0-1
        raw_score_0_10 = float(governance_output.get("overall_governance_score", 0.0) or 0.0)
        llm_score = round(raw_score_0_10 / 10.0, 4)

        hallucination = governance_output.get("governance_flags", {}).get(
            "hallucination_detected", False
        )

        total_tokens = 0
        total_cost = 0.0
        has_any_tokens = False
        has_any_cost = False

        for _, meta in payload["agents"].items():
            tokens = meta.get("tokens")
            cost = meta.get("cost")

            if isinstance(tokens, int):
                total_tokens += tokens
                has_any_tokens = True

            if isinstance(cost, (int, float)):
                total_cost += float(cost)
                has_any_cost = True

        # Seed metrics with the raw LLM governance score
        payload["metrics"] = {
            "total_tokens": total_tokens if has_any_tokens else None,
            "total_cost_usd": round(total_cost, 6) if has_any_cost else None,
            "governance_score_llm": llm_score,
        }

        # This should now compute:
        # - governance_score_llm
        # - governance_score_composite
        # - governance_score (set equal to composite)
        # - structural_quality_score
        # - strategic_depth_index
        # - unsupported_claim_rate
        # - citation_coverage
        primary_metrics = compute_primary_evaluation_metrics(payload)
        payload["metrics"].update(primary_metrics)

        composite_score = payload["metrics"].get("governance_score", llm_score)

        payload["governance_diagnostics"] = {
            "hallucination_detected": hallucination,
            "overall_governance_score_raw_0_10": raw_score_0_10,
            "overall_governance_score_normalized_0_1": llm_score,
            "governance_score_llm": llm_score,
            "governance_score_composite": composite_score,
            "evaluator_type": "independent_clean_llm",
        }

        payload["delivery_status"] = (
            "approved_for_export"
            if composite_score >= GOVERNANCE_APPROVAL_THRESHOLD and not hallucination
            else "internal_review_required"
        )

        await ctx.yield_output(payload)


def create_workflow(use_external_rag: bool = True):
    step_0 = ConsultantIntakeExecutor()
    step_1 = ProblemStructuringExecutor()
    step_2 = RetrievalExecutor(use_external_rag=use_external_rag)
    step_3 = StrategicAnalysisExecutor()
    step_4 = ReportGenerationExecutor()
    step_5 = GovernanceExecutor()

    workflow = (
        WorkflowBuilder(start_executor=step_0)
        .add_edge(step_0, step_1)
        .add_edge(step_1, step_2)
        .add_edge(step_2, step_3)
        .add_edge(step_3, step_4)
        .add_edge(step_4, step_5)
        .build()
    )
    return workflow


class ConsultingWorkflow:
    def __init__(self, architecture: str = "multi_agent_4_dspy", use_external_rag: bool = True):
        self.architecture = architecture
        self.use_external_rag = use_external_rag

    async def run_async(
        self,
        consultant_brief: dict,
        case_id: str | None = None,
    ) -> dict:
        run_id = str(uuid.uuid4())
        case_id = case_id or str(uuid.uuid4())

        run_record = {
            "run_id": run_id,
            "case_id": case_id,
            "architecture": self.architecture,
            "use_external_rag": self.use_external_rag,
            "configuration": build_configuration_snapshot(
                architecture=self.architecture,
                use_external_rag=self.use_external_rag,
            ),
            "success": True,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
            "latency_seconds": {},
            "agents": {},
            "consultant_brief": consultant_brief,
            "intake_assessment": None,
            "case_description": None,
            "problem_structuring_output": None,
            "retrieval": None,
            "strategic_analysis_output": None,
            "report": None,
            "governance_output": None,
            "metrics": {},
            "delivery_status": None,
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

        try:
            save_run_to_sqlite(run_record)
        except Exception:
            pass

        return run_record

    def run(
        self,
        consultant_brief: dict,
        case_id: str | None = None,
    ) -> dict:
        return asyncio.run(self.run_async(consultant_brief, case_id))