import os

from dspy_config import configure_dspy
from workflow import ConsultingWorkflow
from enhanced_run_display import print_run_summary
from export_report_docx import build_docx_from_run_record


def ensure_directory(path: str):
    os.makedirs(path, exist_ok=True)


if __name__ == "__main__":
    configure_dspy()

    consultant_brief = {
        "company_name": "MercadoPlus",
        "geography": "Spain",
        "sector": "grocery retail",
        "sub_sector": "mid-sized supermarket chain",
        "business_model": "brick-and-mortar supermarket chain with regional presence",
        "company_size": "mid-sized",

        "main_problem": "Declining profit margins despite stable revenue, with increasing pressure from discount retailers and supply chain inefficiencies.",
        "symptoms": [
            "Stable top-line revenue but lower operating margin",
            "Rising supply chain and operating costs",
            "Competitive pressure from discount retailers",
            "Concern about preserving customer loyalty and service quality",
        ],
        "suspected_root_causes": [
            "Inefficient supply chain processes",
            "Weak cost-to-serve visibility",
            "Pricing pressure from low-cost competitors",
        ],

        "objectives": [
            "Improve profit margins",
            "Protect customer loyalty",
            "Identify strategic actions with realistic implementation paths",
        ],
        "key_questions": [
            "Which strategic levers could improve margins without damaging customer loyalty?",
            "What operational improvements should be prioritized first?",
            "How should the company respond to discount competitors?",
        ],
        "kpis": [
            "Operating margin",
            "Gross margin",
            "Customer retention",
            "Inventory turnover",
            "Basket size",
        ],

        "time_horizon": "12-24 months",
        "constraints": [
            "Avoid severe deterioration in service quality",
            "Recommendations should be realistic for a mid-sized retailer",
        ],
        "strategic_priorities": [
            "Margin improvement",
            "Operational efficiency",
            "Customer retention",
        ],

        "preferred_source_types": [
            "consulting reports",
            "regulators",
            "industry news",
            "market data",
        ],
        "preferred_domains": [
            "mckinsey.com",
            "bain.com",
            "bcg.com",
            "europa.eu",
            "oecd.org",
        ],
        "banned_domains": [],
        "recency_preference": "Prioritize recent sources from the last 2-3 years, but include older benchmark sources if highly relevant.",

        "preferred_report_style": "board-ready strategic consulting report",
        "preferred_report_length": "medium",
        "extra_context": "The consultant wants actionable recommendations, not only diagnosis.",
    }

    workflow = ConsultingWorkflow(
        architecture="multi_agent_4_dspy",
        use_external_rag=True,
    )

    result = workflow.run(consultant_brief, case_id="case_001")

    print_run_summary(
        result,
        show_agent_outputs=True,
        max_chars_per_output=1500,
    )

    ensure_directory("generated_reports")

    if result.get("delivery_status") == "approved_for_export":
        docx_path = os.path.join(
            "generated_reports",
            f"{result['run_id']}_report.docx"
        )
    else:
        docx_path = os.path.join(
            "generated_reports",
            f"{result['run_id']}_internal_review.docx"
        )

    try:
        build_docx_from_run_record(result, docx_path)
        print(f"Downloadable report generated: {docx_path}")
    except Exception as e:
        print(f"Could not generate DOCX report: {e}")