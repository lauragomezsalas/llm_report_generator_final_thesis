import os

from workflow import ConsultingWorkflow
from enhanced_run_display import print_run_summary
from export_report_docx import build_docx_from_run_record


def ensure_directory(path: str):
    os.makedirs(path, exist_ok=True)


if __name__ == "__main__":
    case = """
    A mid-sized supermarket chain in Spain is experiencing declining profit margins
    despite stable revenue. Competition from discount retailers is intensifying.
    Operational costs have increased due to supply chain inefficiencies.
    The company wants to identify strategic actions to improve margins while
    maintaining customer loyalty and service quality.
    """

    workflow = ConsultingWorkflow(
        architecture="multi_agent_4_microsoft",
        use_external_rag=True,
    )

    result = workflow.run(case, case_id="case_001")

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