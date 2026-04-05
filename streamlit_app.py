import copy
import os
import tempfile
from datetime import datetime
from typing import Any

import streamlit as st

from dspy_config import configure_dspy
from export_report_docx import build_docx_from_run_record
from workflow import ConsultingWorkflow


st.set_page_config(
    page_title="Strategic Consulting Copilot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    .hero {
        padding: 1.2rem 1.3rem;
        border-radius: 22px;
        background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 55%, #60a5fa 100%);
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.20);
    }
    .hero h1 {
        margin: 0;
        font-size: 2rem;
    }
    .hero p {
        margin: 0.45rem 0 0 0;
        opacity: 0.95;
        font-size: 1rem;
    }
    .soft-card {
        background: #f8fafc;
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        margin-bottom: 0.8rem;
    }
    .score-card {
        background: white;
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        min-height: 124px;
    }
    .top-kpi-card {
        background: white;
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 18px;
        padding: 0.85rem 0.95rem;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        min-height: 90px;
    }
    .top-kpi-label {
        color: #64748b;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: .04em;
        margin-bottom: 0.25rem;
        line-height: 1.1;
    }
    .top-kpi-value {
        color: #0f172a;
        font-size: 0.96rem;
        font-weight: 700;
        line-height: 1.25;
        word-break: break-word;
        overflow-wrap: anywhere;
    }
    .status-mini {
        background: #f8fafc;
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
        margin-bottom: 0.55rem;
    }
    .status-mini-label {
        color: #64748b;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: .04em;
        margin-bottom: 0.2rem;
        line-height: 1.1;
    }
    .status-mini-value {
        color: #0f172a;
        font-size: 0.92rem;
        font-weight: 700;
        line-height: 1.25;
        word-break: break-word;
        overflow-wrap: anywhere;
    }
    .section-label {
        color: #475569;
        font-size: 0.84rem;
        text-transform: uppercase;
        letter-spacing: .04em;
        margin-bottom: 0.2rem;
    }
    .metric-big {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .muted {
        color: #64748b;
        font-size: 0.92rem;
    }
    .approved {
        color: #166534;
        font-weight: 700;
    }
    .review {
        color: #991b1b;
        font-weight: 700;
    }
    .report-shell {
        background: white;
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 22px;
        padding: 1.15rem 1.25rem;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
    }
    .brief-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }
    .brief-item {
        background: white;
        border: 1px solid rgba(148, 163, 184, 0.20);
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
    }
    .brief-label {
        color: #64748b;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: .04em;
        margin-bottom: 0.2rem;
    }
    .brief-value {
        color: #0f172a;
        font-size: 0.98rem;
        font-weight: 600;
        line-height: 1.35;
        white-space: pre-wrap;
    }
    .brief-item-wide {
        background: white;
        border: 1px solid rgba(148, 163, 184, 0.20);
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def init_dspy():
    return configure_dspy()


init_dspy()


DEFAULT_BRIEF = {
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


def init_state() -> None:
    if "run_history" not in st.session_state:
        st.session_state.run_history = []
    if "latest_run" not in st.session_state:
        st.session_state.latest_run = None
    if "best_run" not in st.session_state:
        st.session_state.best_run = None
    if "working_brief" not in st.session_state:
        st.session_state.working_brief = copy.deepcopy(DEFAULT_BRIEF)
    if "iteration_notes" not in st.session_state:
        st.session_state.iteration_notes = ""
    if "flash_message" not in st.session_state:
        st.session_state.flash_message = None


init_state()


def lines_to_list(text: str) -> list[str]:
    return [line.strip() for line in str(text).splitlines() if line.strip()]


def list_to_lines(values: list[str] | None) -> str:
    return "\n".join(values or [])


def humanize_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    text = text.replace("_", " ")
    text = " ".join(text.split())
    return text.capitalize()


def score_to_label(score: float | None) -> str:
    if score is None:
        return "No score"
    if score >= 0.8:
        return "Strong"
    if score >= 0.65:
        return "Promising"
    if score >= 0.5:
        return "Borderline"
    return "Weak"


def normalize_brief_from_form(form_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "company_name": form_data["company_name"].strip(),
        "geography": form_data["geography"].strip(),
        "sector": form_data["sector"].strip(),
        "sub_sector": form_data["sub_sector"].strip(),
        "business_model": form_data["business_model"].strip(),
        "company_size": form_data["company_size"].strip(),
        "main_problem": form_data["main_problem"].strip(),
        "symptoms": lines_to_list(form_data["symptoms"]),
        "suspected_root_causes": lines_to_list(form_data["suspected_root_causes"]),
        "objectives": lines_to_list(form_data["objectives"]),
        "key_questions": lines_to_list(form_data["key_questions"]),
        "kpis": lines_to_list(form_data["kpis"]),
        "time_horizon": form_data["time_horizon"].strip(),
        "constraints": lines_to_list(form_data["constraints"]),
        "strategic_priorities": lines_to_list(form_data["strategic_priorities"]),
        "preferred_source_types": lines_to_list(form_data["preferred_source_types"]),
        "preferred_domains": lines_to_list(form_data["preferred_domains"]),
        "banned_domains": lines_to_list(form_data["banned_domains"]),
        "recency_preference": form_data["recency_preference"].strip(),
        "preferred_report_style": form_data["preferred_report_style"].strip(),
        "preferred_report_length": form_data["preferred_report_length"].strip(),
        "extra_context": form_data["extra_context"].strip(),
    }


def run_workflow(brief: dict[str, Any], use_rag: bool, case_id: str | None = None) -> dict[str, Any]:
    workflow = ConsultingWorkflow(
        architecture="multi_agent_4_dspy",
        use_external_rag=use_rag,
    )
    return workflow.run(brief, case_id=case_id)


def get_run_score(result: dict[str, Any] | None) -> float | None:
    if not result:
        return None
    metrics = result.get("metrics", {}) or {}
    score = metrics.get("governance_score")
    return float(score) if isinstance(score, (int, float)) else None


def store_run(result: dict[str, Any], brief: dict[str, Any], label: str, prefer_if_better: bool = False) -> bool:
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "label": label,
        "brief": copy.deepcopy(brief),
        "result": result,
    }
    st.session_state.run_history.append(record)
    st.session_state.working_brief = copy.deepcopy(brief)

    previous_latest = st.session_state.latest_run
    improved = True

    if prefer_if_better and previous_latest is not None:
        new_score = get_run_score(result)
        old_score = get_run_score(previous_latest["result"])
        if old_score is not None and new_score is not None and new_score < old_score:
            st.session_state.latest_run = previous_latest
            improved = False
        else:
            st.session_state.latest_run = record
    else:
        st.session_state.latest_run = record

    best_run = st.session_state.best_run
    best_score = get_run_score(best_run["result"]) if best_run else None
    new_score = get_run_score(result)
    if best_run is None or (new_score is not None and (best_score is None or new_score >= best_score)):
        st.session_state.best_run = record

    return improved


def render_top_summary_cards(record: dict[str, Any]) -> None:
    result = record["result"]
    score = get_run_score(result)
    cards = [
        ("Latest client", record["brief"].get("company_name", "-")),
        ("Latest score", f"{score:.2f}" if score is not None else "-"),
        ("Delivery status", humanize_text(result.get("delivery_status", "-"))),
        ("Runs this session", str(len(st.session_state.run_history))),
    ]
    cols = st.columns(4)
    for col, (label, value) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="top-kpi-card">
                    <div class="top-kpi-label">{label}</div>
                    <div class="top-kpi-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_brief_summary(brief: dict[str, Any]) -> None:
    st.markdown("<div class='soft-card'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="brief-grid">
            <div class="brief-item">
                <div class="brief-label">Client</div>
                <div class="brief-value">{brief.get('company_name', '-') or '-'}</div>
            </div>
            <div class="brief-item">
                <div class="brief-label">Geography</div>
                <div class="brief-value">{brief.get('geography', '-') or '-'}</div>
            </div>
            <div class="brief-item">
                <div class="brief-label">Time horizon</div>
                <div class="brief-value">{brief.get('time_horizon', '-') or '-'}</div>
            </div>
        </div>
        <div class="brief-item-wide">
            <div class="brief-label">Main problem</div>
            <div class="brief-value">{brief.get('main_problem', '-') or '-'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_governance_dashboard(result: dict[str, Any]) -> None:
    metrics = result.get("metrics", {}) or {}
    diag = result.get("governance_diagnostics", {}) or {}
    delivery_status = result.get("delivery_status") or "unknown"

    status_text = "Approved for export" if delivery_status == "approved_for_export" else "Internal review required"
    status_class = "approved" if delivery_status == "approved_for_export" else "review"

    score = metrics.get("governance_score")
    structural = metrics.get("structural_quality_score")
    depth = metrics.get("strategic_depth_index")
    citation = metrics.get("citation_coverage")
    unsupported = metrics.get("unsupported_claim_rate")

    st.markdown(f"<p class='{status_class}'>{status_text}</p>", unsafe_allow_html=True)

    cols = st.columns(4)
    values = [
        ("Composite governance", score, "Release decision score used by the app"),
        ("Structural quality", structural, "Schema, completeness, KPI and citation alignment"),
        ("Strategic depth", depth, "Alternatives, trade-offs, quantification and alignment"),
        ("Citation coverage", citation, "Share of report claims that appear cited"),
    ]

    for col, (title, value, subtitle) in zip(cols, values):
        with col:
            st.markdown("<div class='score-card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='section-label'>{title}</div>", unsafe_allow_html=True)
            display_value = "-" if value is None else f"{float(value):.2f}"
            st.markdown(f"<div class='metric-big'>{display_value}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='muted'>{subtitle}</div>", unsafe_allow_html=True)
            if isinstance(value, (int, float)):
                st.progress(max(0.0, min(1.0, float(value))))
            st.markdown("</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("### Release notes")
        st.write(f"**Assessment:** {score_to_label(score)}")
        st.write(f"**Unsupported claim rate:** {unsupported if unsupported is not None else '-'}")
        st.write(f"**Hallucination detected:** {diag.get('hallucination_detected', False)}")
    with col_b:
        st.markdown("### Recommended next step")
        if delivery_status == "approved_for_export":
            st.success("The report is strong enough to export or client-polish.")
        else:
            st.warning(
                "Use the iteration panel to add tighter objectives, sharper KPIs, or explicit improvement instructions before rerunning."
            )


def render_report(report: dict[str, Any]) -> None:
    if not report:
        st.info("No report has been generated yet.")
        return

    st.markdown("<div class='report-shell'>", unsafe_allow_html=True)
    st.markdown("## Strategic report")

    st.markdown("### Executive summary")
    st.write(report.get("executive_summary", "-"))

    insights = report.get("key_insights", []) or []
    if insights:
        st.markdown("### Key insights")
        for insight in insights:
            st.markdown(f"- {insight}")

    st.markdown("### Company and market overview")
    st.write(report.get("company_and_market_overview", "-"))

    alternatives = report.get("strategic_alternatives_section", []) or []
    if alternatives:
        st.markdown("### Strategic alternatives")
        for idx, alt in enumerate(alternatives, start=1):
            with st.expander(f"Alternative {idx}: {alt.get('title', f'Alternative {idx}')}", expanded=(idx == 1)):
                st.write(f"**ID:** {alt.get('id', '-')}")
                st.write(f"**Strategic rationale:** {alt.get('strategic_rationale', '-')}")
                st.write(f"**Expected impact:** {alt.get('expected_impact_summary', '-')}")
                st.write(f"**Key risks:** {alt.get('risk_summary', '-')}")
                evidence_ids = alt.get("evidence_ids", []) or []
                if evidence_ids:
                    st.caption("Evidence IDs: " + ", ".join(evidence_ids))
                citations = alt.get("apa_citations", []) or []
                if citations:
                    st.caption("Citations: " + "; ".join(citations))

    st.markdown("### Trade-off discussion")
    st.write(report.get("trade_off_discussion", "-"))

    fin = report.get("financial_impact_summary", []) or []
    if fin:
        st.markdown("### Financial impact summary")
        for item in fin:
            st.markdown(f"**{item.get('metric', 'Metric')}:** {item.get('estimate', '-')}")
            st.write(item.get("rationale", "-"))
            cites = item.get("apa_citations", []) or []
            if cites:
                st.caption("Citations: " + "; ".join(cites))
            st.divider()

    final_rec = report.get("final_recommendation", {}) or {}
    st.markdown("### Final recommendation")
    st.write(f"**Selected alternative:** {final_rec.get('selected_alternative', '-')}")
    st.write(final_rec.get("justification", "-"))
    st.write(f"**Implementation roadmap summary:** {final_rec.get('implementation_roadmap_summary', '-')}")

    timeline = report.get("implementation_timeline", []) or []
    if timeline:
        st.markdown("### Implementation timeline")
        for idx, phase in enumerate(timeline, start=1):
            with st.expander(f"Phase {idx}: {phase.get('phase_title', f'Phase {idx}')} | {phase.get('timeline', '-')}"):
                if phase.get("objectives"):
                    st.write("**Objectives**")
                    for x in phase.get("objectives", []):
                        st.markdown(f"- {x}")
                if phase.get("key_actions"):
                    st.write("**Key actions**")
                    for x in phase.get("key_actions", []):
                        st.markdown(f"- {x}")
                if phase.get("expected_outputs"):
                    st.write("**Expected outputs**")
                    for x in phase.get("expected_outputs", []):
                        st.markdown(f"- {x}")

    risks = report.get("risks_and_mitigation", []) or []
    if risks:
        st.markdown("### Risks and mitigation")
        for idx, item in enumerate(risks, start=1):
            with st.expander(f"Risk {idx}: {item.get('risk', f'Risk {idx}')}"):
                st.write(f"**Severity:** {item.get('severity', '-')}")
                st.write(f"**Mitigation:** {item.get('mitigation', '-')}")
                cites = item.get("apa_citations", []) or []
                if cites:
                    st.caption("Citations: " + "; ".join(cites))

    st.markdown("### Conclusion")
    st.write(report.get("conclusion", "-"))

    refs = report.get("references", []) or []
    if refs:
        with st.expander("References"):
            for ref in refs:
                st.markdown(f"- {ref}")

    st.markdown("</div>", unsafe_allow_html=True)


def render_retrieval(retrieval: dict[str, Any]) -> None:
    docs = retrieval.get("documents", []) if isinstance(retrieval, dict) else []
    if not docs:
        st.info("No evidence bundle available.")
        return

    meta_cols = st.columns(4)
    meta_cols[0].metric("Retrieved documents", len(docs))
    meta_cols[1].metric("Cache hit", str(retrieval.get("cache_hit", False)))
    latency = retrieval.get("retrieval_latency")
    meta_cols[2].metric("Retrieval latency", f"{latency}s" if latency is not None else "-")
    meta_cols[3].metric("Query used", "Available")
    st.caption(retrieval.get("query", ""))

    for doc in docs:
        with st.expander(f"{doc.get('evidence_id', '-')}: {doc.get('title', 'Untitled source')}"):
            st.write(f"**Source domain:** {doc.get('source_domain', '-')}")
            st.write(f"**Relevance score:** {doc.get('relevance_score', '-')}")
            link = doc.get("link")
            if link:
                st.markdown(f"**Link:** {link}")
            st.write(doc.get("snippet", ""))
            content = doc.get("content", "")
            if content:
                st.text_area("Content extract", value=content[:2000], height=180, key=f"content_{doc.get('evidence_id')}")
            ref = doc.get("apa_reference")
            if ref:
                st.caption(ref)


def build_iteration_brief(base_brief: dict[str, Any], feedback: str, latest_result: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(base_brief)
    prior_context = updated.get("extra_context", "").strip()
    feedback = feedback.strip()

    metrics = (latest_result or {}).get("metrics", {}) or {}
    governance_output = (latest_result or {}).get("governance_output", {}) or {}
    governance_flags = (governance_output.get("governance_flags", {}) or {}).get("unsupported_claims", []) or []
    structural = metrics.get("structural_quality_score")
    depth = metrics.get("strategic_depth_index")
    citation = metrics.get("citation_coverage")
    unsupported = metrics.get("unsupported_claim_rate")
    delivery_status = humanize_text((latest_result or {}).get("delivery_status", ""))

    machine_guidance = [
        "Consultant iteration request:",
        feedback,
        "Machine improvement goals for the next draft:",
        f"- Improve the overall governance score relative to the previous draft.",
        f"- Current delivery status: {delivery_status}.",
        f"- Current structural quality score: {structural if structural is not None else '-'}.",
        f"- Current strategic depth index: {depth if depth is not None else '-'}.",
        f"- Current citation coverage: {citation if citation is not None else '-'}.",
        f"- Current unsupported claim rate: {unsupported if unsupported is not None else '-'}.",
        "- Strengthen trade-off analysis, sharpen the recommendation, and make the implementation roadmap more actionable.",
        "- Reduce generic wording, preserve evidence discipline, and directly address flagged weaknesses.",
    ]
    if governance_flags:
        machine_guidance.append("- Explicitly fix these flagged unsupported claims or remove them if not grounded:")
        machine_guidance.extend([f"  * {claim}" for claim in governance_flags[:8]])

    additions = [part for part in [prior_context, "\n".join([x for x in machine_guidance if x])] if part]
    updated["extra_context"] = "\n\n".join(additions)
    return updated


def export_docx_download(result: dict[str, Any]) -> None:
    if not result:
        st.info("Run a report first.")
        return

    run_id = result.get("run_id", "consulting_report")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        output_path = build_docx_from_run_record(result, tmp.name)

    with open(output_path, "rb") as f:
        st.download_button(
            label="Download DOCX report",
            data=f.read(),
            file_name=f"{run_id}_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    try:
        os.remove(output_path)
    except OSError:
        pass


def compare_runs(current_result: dict[str, Any], prior_result: dict[str, Any]) -> None:
    current_metrics = (current_result or {}).get("metrics", {}) or {}
    prior_metrics = (prior_result or {}).get("metrics", {}) or {}

    rows = [
        ("Governance score", "governance_score"),
        ("Structural quality", "structural_quality_score"),
        ("Strategic depth", "strategic_depth_index"),
        ("Citation coverage", "citation_coverage"),
        ("Unsupported claim rate", "unsupported_claim_rate"),
    ]

    for label, key in rows:
        new_val = current_metrics.get(key)
        old_val = prior_metrics.get(key)
        delta = None
        if isinstance(new_val, (int, float)) and isinstance(old_val, (int, float)):
            delta = new_val - old_val
        st.metric(label, value=(f"{new_val:.2f}" if isinstance(new_val, (int, float)) else "-"), delta=(f"{delta:+.2f}" if delta is not None else None))


def render_machine_status_panel(result: dict[str, Any]) -> None:
    metrics = result.get("metrics", {}) or {}
    cards = [
        ("Current governance score", f"{metrics.get('governance_score', 0):.2f}" if isinstance(metrics.get("governance_score"), (int, float)) else "-"),
        ("Current delivery status", humanize_text(result.get("delivery_status", "-"))),
        ("Unsupported claim rate", f"{metrics.get('unsupported_claim_rate', 0):.2f}" if isinstance(metrics.get("unsupported_claim_rate"), (int, float)) else "-"),
        ("Citation coverage", f"{metrics.get('citation_coverage', 0):.2f}" if isinstance(metrics.get("citation_coverage"), (int, float)) else "-"),
    ]
    for label, value in cards:
        st.markdown(
            f"""
            <div class="status-mini">
                <div class="status-mini-label">{label}</div>
                <div class="status-mini-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.sidebar.title("Engagement controls")
use_rag = st.sidebar.toggle("Use external RAG", value=True)
show_json = st.sidebar.toggle("Show raw JSON panels", value=False)
show_retrieval = st.sidebar.toggle("Show evidence bundle", value=True)

st.sidebar.markdown("---")
st.sidebar.caption("This UI is built around your existing intake, workflow, governance and DOCX export pipeline.")

if st.sidebar.button("Reset working brief", use_container_width=True):
    st.session_state.working_brief = copy.deepcopy(DEFAULT_BRIEF)
    st.rerun()

if st.sidebar.button("Clear run history", use_container_width=True):
    st.session_state.run_history = []
    st.session_state.latest_run = None
    st.session_state.best_run = None
    st.rerun()


st.markdown(
    """
    <div class="hero">
        <h1>Strategic Consulting Copilot</h1>
        <p>Structured client intake, grounded analysis, governance scoring, and an interactive consultant-in-the-loop revision cycle.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.flash_message:
    level = st.session_state.flash_message.get("level", "info")
    message = st.session_state.flash_message.get("text", "")
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.info(message)
    st.session_state.flash_message = None

latest_record = st.session_state.latest_run
if latest_record:
    render_top_summary_cards(latest_record)


tab_brief, tab_results, tab_iterate, tab_history = st.tabs([
    "Case intake",
    "Report workspace",
    "Human-in-the-loop revision",
    "Run history",
])


with tab_brief:
    st.subheader("Client brief")
    base = st.session_state.working_brief

    with st.form("consultant_intake_form"):
        top1, top2 = st.columns(2)
        with top1:
            company_name = st.text_input("Company name", value=base.get("company_name", ""))
            geography = st.text_input("Geography", value=base.get("geography", ""))
            sector = st.text_input("Sector", value=base.get("sector", ""))
            sub_sector = st.text_input("Sub-sector", value=base.get("sub_sector", ""))
            business_model = st.text_input("Business model", value=base.get("business_model", ""))
            company_size = st.text_input("Company size", value=base.get("company_size", ""))
            time_horizon = st.text_input("Time horizon", value=base.get("time_horizon", ""))
            preferred_report_style = st.text_input("Preferred report style", value=base.get("preferred_report_style", ""))
            preferred_report_length = st.selectbox(
                "Preferred report length",
                options=["short", "medium", "long"],
                index=["short", "medium", "long"].index(base.get("preferred_report_length", "medium")) if base.get("preferred_report_length", "medium") in ["short", "medium", "long"] else 1,
            )

        with top2:
            main_problem = st.text_area("Main problem", value=base.get("main_problem", ""), height=110)
            extra_context = st.text_area("Additional context / partner notes", value=base.get("extra_context", ""), height=180)
            recency_preference = st.text_input("Recency preference", value=base.get("recency_preference", ""))

        mid1, mid2, mid3 = st.columns(3)
        with mid1:
            symptoms = st.text_area("Symptoms (one per line)", value=list_to_lines(base.get("symptoms")), height=180)
            objectives = st.text_area("Objectives (one per line)", value=list_to_lines(base.get("objectives")), height=180)
        with mid2:
            suspected_root_causes = st.text_area("Suspected root causes (one per line)", value=list_to_lines(base.get("suspected_root_causes")), height=180)
            key_questions = st.text_area("Key strategic questions (one per line)", value=list_to_lines(base.get("key_questions")), height=180)
        with mid3:
            kpis = st.text_area("Priority KPIs (one per line)", value=list_to_lines(base.get("kpis")), height=180)
            strategic_priorities = st.text_area("Strategic priorities (one per line)", value=list_to_lines(base.get("strategic_priorities")), height=180)

        bottom1, bottom2, bottom3 = st.columns(3)
        with bottom1:
            constraints = st.text_area("Constraints (one per line)", value=list_to_lines(base.get("constraints")), height=140)
        with bottom2:
            preferred_source_types = st.text_area("Preferred source types (one per line)", value=list_to_lines(base.get("preferred_source_types")), height=140)
        with bottom3:
            preferred_domains = st.text_area("Preferred domains (one per line)", value=list_to_lines(base.get("preferred_domains")), height=90)
            banned_domains = st.text_area("Banned domains (one per line)", value=list_to_lines(base.get("banned_domains")), height=90)

        left, right = st.columns([1, 1])
        run_clicked = left.form_submit_button("Run report", type="primary", use_container_width=True)
        save_clicked = right.form_submit_button("Save brief only", use_container_width=True)

        form_payload = {
            "company_name": company_name,
            "geography": geography,
            "sector": sector,
            "sub_sector": sub_sector,
            "business_model": business_model,
            "company_size": company_size,
            "main_problem": main_problem,
            "symptoms": symptoms,
            "suspected_root_causes": suspected_root_causes,
            "objectives": objectives,
            "key_questions": key_questions,
            "kpis": kpis,
            "time_horizon": time_horizon,
            "constraints": constraints,
            "strategic_priorities": strategic_priorities,
            "preferred_source_types": preferred_source_types,
            "preferred_domains": preferred_domains,
            "banned_domains": banned_domains,
            "recency_preference": recency_preference,
            "preferred_report_style": preferred_report_style,
            "preferred_report_length": preferred_report_length,
            "extra_context": extra_context,
        }

        if save_clicked or run_clicked:
            normalized_brief = normalize_brief_from_form(form_payload)
            st.session_state.working_brief = copy.deepcopy(normalized_brief)
            if save_clicked:
                st.session_state.flash_message = {"level": "success", "text": "Working brief saved."}
                st.rerun()

        if run_clicked:
            brief = normalize_brief_from_form(form_payload)
            with st.spinner("Running consulting workflow..."):
                result = run_workflow(brief=brief, use_rag=use_rag)
            store_run(result=result, brief=brief, label="Initial run")
            st.session_state.flash_message = {
                "level": "success",
                "text": "Run completed. The report workspace is now populated with the latest report.",
            }
            st.rerun()

    st.caption("Use this tab to structure the case like a consultant brief. The app then passes that brief into your existing intake and workflow pipeline.")


with tab_results:
    st.subheader("Report workspace")
    latest_record = st.session_state.latest_run
    if not latest_record:
        st.info("Run the case once to open the report workspace.")
    else:
        current_result = latest_record["result"]
        current_brief = latest_record["brief"]

        render_brief_summary(current_brief)
        render_governance_dashboard(current_result)

        action1, action2 = st.columns([1, 1])
        with action1:
            export_docx_download(current_result)
        with action2:
            if st.button("Load this brief back into intake", use_container_width=True):
                st.session_state.working_brief = copy.deepcopy(current_brief)
                st.session_state.flash_message = {"level": "success", "text": "The current brief has been loaded into the intake tab for editing."}
                st.rerun()

        report_tab, evidence_tab, machine_tab = st.tabs(["Formatted report", "Evidence bundle", "Machine diagnostics"])
        with report_tab:
            render_report(current_result.get("report", {}) or {})
        with evidence_tab:
            if show_retrieval:
                render_retrieval(current_result.get("retrieval", {}) or {})
            else:
                st.info("Enable 'Show evidence bundle' in the sidebar to inspect retrieved sources.")
        with machine_tab:
            st.markdown("### Delivery decision")
            st.json({
                "delivery_status": humanize_text(current_result.get("delivery_status")),
                "governance_diagnostics": current_result.get("governance_diagnostics", {}),
                "agents": current_result.get("agents", {}),
                "latency_seconds": current_result.get("latency_seconds", {}),
            })
            if show_json:
                st.markdown("### Full run JSON")
                st.json(current_result)


with tab_iterate:
    st.subheader("Human-in-the-loop revision")
    latest_record = st.session_state.latest_run
    if not latest_record:
        st.info("Run an initial report first. Then you can guide the next version with explicit consultant feedback.")
    else:
        last_brief = latest_record["brief"]
        last_result = latest_record["result"]

        left, right = st.columns([1.15, 0.85])
        with left:
            st.markdown("### Consultant feedback to the machine")
            st.write(
                "Tell the system what to improve. Examples: sharpen the recommendation, reduce generic wording, focus more on operating margin, add more realistic implementation risks, or better compare alternatives."
            )
            feedback = st.text_area(
                "Revision instructions",
                value=st.session_state.iteration_notes,
                height=220,
                placeholder=(
                    "Example:\n"
                    "- Make the recommendation more decisive.\n"
                    "- Emphasize margin impact and inventory turnover.\n"
                    "- Add clearer trade-offs between pricing actions and customer retention risk.\n"
                    "- Reduce generic statements and make the roadmap more actionable."
                ),
            )
            st.session_state.iteration_notes = feedback

            rerun_cols = st.columns([1, 1])
            if rerun_cols[0].button("Run revised version", type="primary", use_container_width=True):
                revised_brief = build_iteration_brief(last_brief, feedback, last_result)
                with st.spinner("Running revised workflow..."):
                    revised_result = run_workflow(
                        brief=revised_brief,
                        use_rag=use_rag,
                        case_id=last_result.get("case_id"),
                    )
                improved = store_run(
                    result=revised_result,
                    brief=revised_brief,
                    label="Revision run",
                    prefer_if_better=True,
                )
                if improved:
                    st.session_state.flash_message = {
                        "level": "success",
                        "text": "Revised version completed and the workspace has been updated with the improved run.",
                    }
                else:
                    st.session_state.flash_message = {
                        "level": "warning",
                        "text": "A revised run was generated, but it scored below the current workspace version. The workspace kept the stronger report while the weaker revision was still saved in run history.",
                    }
                st.rerun()

            if rerun_cols[1].button("Push notes into intake only", use_container_width=True):
                revised_brief = build_iteration_brief(last_brief, feedback, last_result)
                st.session_state.working_brief = revised_brief
                st.session_state.flash_message = {"level": "success", "text": "Revision notes were added to the working brief in the intake tab."}
                st.rerun()

        with right:
            st.markdown("### Current machine status")
            render_machine_status_panel(last_result)

            flags = ((last_result.get("governance_output", {}) or {}).get("governance_flags", {}) or {})
            claims = flags.get("unsupported_claims", []) or []
            if claims:
                st.markdown("### Governance flags")
                for claim in claims[:8]:
                    st.markdown(f"- {claim}")
            else:
                st.success("No unsupported claims were explicitly flagged in the latest governance review.")

        if len(st.session_state.run_history) >= 2:
            st.markdown("### Improvement vs previous run")
            compare_runs(
                current_result=st.session_state.run_history[-1]["result"],
                prior_result=st.session_state.run_history[-2]["result"],
            )
            best_record = st.session_state.best_run
            if best_record is not None and best_record != st.session_state.latest_run:
                st.info("The best-scoring report in this session is preserved separately, even when a revision run underperforms.")


with tab_history:
    st.subheader("Run history")
    if not st.session_state.run_history:
        st.info("No runs in this session yet.")
    else:
        for idx, record in enumerate(reversed(st.session_state.run_history), start=1):
            result = record["result"]
            metrics = result.get("metrics", {}) or {}
            title = f"{idx}. {humanize_text(record['label'])} | {record['timestamp']} | {record['brief'].get('company_name', '-') }"
            with st.expander(title, expanded=(idx == 1)):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Governance", f"{metrics.get('governance_score', 0):.2f}" if isinstance(metrics.get("governance_score"), (int, float)) else "-")
                col2.metric("Structural", f"{metrics.get('structural_quality_score', 0):.2f}" if isinstance(metrics.get("structural_quality_score"), (int, float)) else "-")
                col3.metric("Depth", f"{metrics.get('strategic_depth_index', 0):.2f}" if isinstance(metrics.get("strategic_depth_index"), (int, float)) else "-")
                col4.metric("Status", humanize_text(result.get("delivery_status", "-")))
                st.write(f"**Problem:** {record['brief'].get('main_problem', '-')}")
                st.write(f"**Extra context:** {record['brief'].get('extra_context', '-')}")

                action_col1, action_col2 = st.columns([1, 1])
                if action_col1.button(f"Load run {idx} into workspace", key=f"load_{idx}", use_container_width=True):
                    st.session_state.latest_run = record
                    st.session_state.working_brief = copy.deepcopy(record["brief"])
                    st.session_state.flash_message = {"level": "success", "text": "Run loaded into the workspace."}
                    st.rerun()
                if action_col2.button(f"Use brief {idx} as new starting point", key=f"brief_{idx}", use_container_width=True):
                    st.session_state.working_brief = copy.deepcopy(record["brief"])
                    st.session_state.flash_message = {"level": "success", "text": "Brief copied back to intake."}
                    st.rerun()

                if show_json:
                    st.json(result)