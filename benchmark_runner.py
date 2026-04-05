import csv
import traceback
from datetime import datetime
from pathlib import Path

from dspy_config import configure_dspy
from workflow import ConsultingWorkflow
from benchmark_cases import BENCHMARK_CASES

# Change this in each code version
EXPERIMENT_LABEL = "version_A"

# Only 1 run per case
CONFIGS = [
    {
        "config_label": "main_run",
        "architecture": "multi_agent_4_dspy",
        "use_external_rag": True,
    }
]


def flatten_result(result: dict, experiment_label: str, config_label: str) -> dict:
    metrics = result.get("metrics", {}) or {}
    latency = result.get("latency_seconds", {}) or {}
    diag = result.get("governance_diagnostics", {}) or {}
    agents = result.get("agents", {}) or {}
    retrieval = result.get("retrieval", {}) or {}
    governance_output = result.get("governance_output", {}) or {}
    governance_flags = (governance_output.get("governance_flags", {}) or {})

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "experiment_label": experiment_label,
        "config_label": config_label,
        "run_id": result.get("run_id"),
        "case_id": result.get("case_id"),
        "company_name": (result.get("consultant_brief", {}) or {}).get("company_name"),
        "geography": (result.get("consultant_brief", {}) or {}).get("geography"),
        "main_problem": (result.get("consultant_brief", {}) or {}).get("main_problem"),
        "success": result.get("success"),
        "delivery_status": result.get("delivery_status"),
        "governance_score": metrics.get("governance_score"),
        "governance_score_llm": metrics.get("governance_score_llm"),
        "governance_score_composite": metrics.get("governance_score_composite"),
        "structural_quality_score": metrics.get("structural_quality_score"),
        "strategic_depth_index": metrics.get("strategic_depth_index"),
        "unsupported_claim_rate": metrics.get("unsupported_claim_rate"),
        "citation_coverage": metrics.get("citation_coverage"),
        "hallucination_detected": diag.get("hallucination_detected"),
        "unsupported_claims_count": len(governance_flags.get("unsupported_claims", []) or []),
        "total_latency_seconds": latency.get("total"),
        "total_cost_usd": metrics.get("total_cost_usd"),
        "total_tokens": metrics.get("total_tokens"),
        "intake_latency": (agents.get("intake", {}) or {}).get("latency"),
        "agent_1_latency": (agents.get("agent_1", {}) or {}).get("latency"),
        "retrieval_latency": (agents.get("retrieval", {}) or {}).get("latency"),
        "agent_2_latency": (agents.get("agent_2", {}) or {}).get("latency"),
        "agent_3_latency": (agents.get("agent_3", {}) or {}).get("latency"),
        "agent_4_latency": (agents.get("agent_4", {}) or {}).get("latency"),
        "retrieval_cache_hit": retrieval.get("cache_hit"),
        "retrieval_docs_count": len(retrieval.get("documents", []) or []),
        "retrieval_query": retrieval.get("query"),
        "fallback_query_used": retrieval.get("fallback_query_used"),
        "error": result.get("error"),
    }


def build_failure_result(case_id: str, brief: dict, err: Exception) -> dict:
    return {
        "run_id": None,
        "case_id": case_id,
        "consultant_brief": brief,
        "success": False,
        "delivery_status": None,
        "metrics": {},
        "latency_seconds": {},
        "governance_diagnostics": {},
        "agents": {},
        "retrieval": {},
        "governance_output": {},
        "error": f"{type(err).__name__}: {str(err)}\n\n{traceback.format_exc()}",
    }


def run_benchmark():
    configure_dspy()

    output_dir = Path("benchmark_outputs")
    output_dir.mkdir(exist_ok=True)

    output_csv = output_dir / f"benchmark_results_{EXPERIMENT_LABEL}.csv"

    rows = []

    print("=" * 80)
    print(f"STARTING BENCHMARK: {EXPERIMENT_LABEL}")
    print("=" * 80)

    for config in CONFIGS:
        config_label = config["config_label"]
        architecture = config["architecture"]
        use_external_rag = config["use_external_rag"]

        print(f"\n--- CONFIG: {config_label} | architecture={architecture} | use_external_rag={use_external_rag} ---")

        workflow = ConsultingWorkflow(
            architecture=architecture,
            use_external_rag=use_external_rag,
        )

        for case in BENCHMARK_CASES:
            run_case_id = case["case_id"]
            brief = case["brief"]

            print(f"Running case: {run_case_id}")

            try:
                result = workflow.run(brief, case_id=run_case_id)
            except Exception as err:
                result = build_failure_result(run_case_id, brief, err)

            row = flatten_result(
                result=result,
                experiment_label=EXPERIMENT_LABEL,
                config_label=config_label,
            )
            rows.append(row)

    if not rows:
        print("No rows were generated.")
        return

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 80)
    print(f"BENCHMARK COMPLETE: {EXPERIMENT_LABEL}")
    print(f"Saved CSV to: {output_csv}")
    print(f"Total runs: {len(rows)}")
    print("=" * 80)


if __name__ == "__main__":
    run_benchmark()