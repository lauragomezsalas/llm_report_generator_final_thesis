import time
import uuid
import traceback
from datetime import datetime

from problem_structuring import run_problem_structuring
from strategic_analysis import run_strategic_analysis
from report_generation import run_report_generation
from governance_agent import run_governance_evaluation
from retrieval_external import retrieve_external_context
from logging_utils import save_full_run, append_metrics_row


COST_PER_1K_INPUT = 0.0015
COST_PER_1K_OUTPUT = 0.002


def estimate_cost(usage):
    input_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens

    return (
        (input_tokens / 1000) * COST_PER_1K_INPUT +
        (output_tokens / 1000) * COST_PER_1K_OUTPUT
    )


class Orchestrator:

    def __init__(self,
                 architecture="multi_agent_4",
                 use_external_rag=False):

        self.architecture = architecture
        self.use_external_rag = use_external_rag

    def run(self, case_description, case_id=None):

        run_id = str(uuid.uuid4())
        case_id = case_id or str(uuid.uuid4())

        run_record = {
            "run_id": run_id,
            "case_id": case_id,
            "architecture": self.architecture,
            "use_external_rag": self.use_external_rag,
            "timestamp": datetime.utcnow().isoformat(),
            "agents": {},
            "retrieval": None,
            "metrics": {
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "governance_score": None,
                "hallucination_detected": None
            },
            "latency_seconds": {},
            "success": True,
            "error": None
        }

        total_start = time.time()
        total_tokens = 0
        total_cost = 0

        try:

            # ---------------- Agent 1 ----------------
            start = time.time()
            a1_output, a1_usage = run_problem_structuring(case_description)
            latency = time.time() - start

            cost = estimate_cost(a1_usage)

            total_tokens += a1_usage.total_tokens
            total_cost += cost

            run_record["agents"]["agent_1"] = {
                "latency": latency,
                "tokens": a1_usage.total_tokens,
                "cost": round(cost, 6),
                "valid_output": isinstance(a1_output, dict)
            }

            # ---------------- Retrieval Layer ----------------
            retrieval_info = None

            if self.use_external_rag:
                retrieval_info = retrieve_external_context(a1_output)
                run_record["retrieval"] = retrieval_info

            # ---------------- Agent 2 ----------------
            start = time.time()
            a2_output, a2_usage = run_strategic_analysis(a1_output, retrieval_info)
            latency = time.time() - start

            cost = estimate_cost(a2_usage)

            total_tokens += a2_usage.total_tokens
            total_cost += cost

            run_record["agents"]["agent_2"] = {
                "latency": latency,
                "tokens": a2_usage.total_tokens,
                "cost": round(cost, 6),
                "valid_output": isinstance(a2_output, dict)
            }

            # ---------------- Agent 3 ----------------
            start = time.time()
            a3_output, a3_usage = run_report_generation(a1_output, a2_output)
            latency = time.time() - start

            cost = estimate_cost(a3_usage)

            total_tokens += a3_usage.total_tokens
            total_cost += cost

            run_record["agents"]["agent_3"] = {
                "latency": latency,
                "tokens": a3_usage.total_tokens,
                "cost": round(cost, 6),
                "valid_output": isinstance(a3_output, dict)
            }

            # ---------------- Agent 4 ----------------
            start = time.time()
            a4_output, a4_usage = run_governance_evaluation(a1_output, a2_output, a3_output)
            latency = time.time() - start

            cost = estimate_cost(a4_usage)

            total_tokens += a4_usage.total_tokens
            total_cost += cost

            run_record["agents"]["agent_4"] = {
                "latency": latency,
                "tokens": a4_usage.total_tokens,
                "cost": round(cost, 6),
                "valid_output": isinstance(a4_output, dict)
            }

            # ---------------- Governance Metrics ----------------
            governance_score = a4_output.get("overall_governance_score")
            hallucination_flag = a4_output.get("governance_flags", {}).get("hallucination_detected")

            run_record["metrics"] = {
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 6),
                "governance_score": governance_score,
                "hallucination_detected": hallucination_flag
            }

        except Exception:
            run_record["success"] = False
            run_record["error"] = traceback.format_exc()

        run_record["latency_seconds"]["total"] = round(time.time() - total_start, 4)

        save_full_run(run_record)
        append_metrics_row(run_record)

        return run_record


