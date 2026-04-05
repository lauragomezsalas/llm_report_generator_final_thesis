from __future__ import annotations

from schemas import ConsultantBrief, IntakeAssessment, ClarificationQuestion


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "Not provided."
    return "\n".join([f"- {item}" for item in items if str(item).strip()])


def render_case_description(brief: ConsultantBrief) -> str:
    return f"""
CLIENT CASE BRIEF

1. Company Profile
Company name: {brief.company_name}
Geography: {brief.geography}
Sector: {brief.sector}
Sub-sector: {brief.sub_sector or "Not provided"}
Business model: {brief.business_model or "Not provided"}
Company size: {brief.company_size or "Not provided"}

2. Main Problem
Primary problem: {brief.main_problem}

Symptoms:
{_bullet_list(brief.symptoms)}

Suspected root causes:
{_bullet_list(brief.suspected_root_causes)}

3. Objectives
Objectives:
{_bullet_list(brief.objectives)}

Key strategic questions:
{_bullet_list(brief.key_questions)}

Priority KPIs:
{_bullet_list(brief.kpis)}

4. Constraints and Preferences
Time horizon: {brief.time_horizon or "Not provided"}

Constraints:
{_bullet_list(brief.constraints)}

Strategic priorities:
{_bullet_list(brief.strategic_priorities)}

5. Source Preferences
Preferred source types:
{_bullet_list(brief.preferred_source_types)}

Preferred domains:
{_bullet_list(brief.preferred_domains)}

Banned domains:
{_bullet_list(brief.banned_domains)}

Recency preference: {brief.recency_preference or "Not provided"}

6. Deliverable Preferences
Preferred report style: {brief.preferred_report_style or "Not provided"}
Preferred report length: {brief.preferred_report_length or "Not provided"}

7. Additional Context
{brief.extra_context or "Not provided."}
""".strip()


def assess_brief(brief: ConsultantBrief) -> IntakeAssessment:
    missing_critical_fields = []

    if not brief.company_name.strip():
        missing_critical_fields.append("company_name")
    if not brief.geography.strip():
        missing_critical_fields.append("geography")
    if not brief.main_problem.strip():
        missing_critical_fields.append("main_problem")

    clarifying_questions = []

    if not brief.objectives:
        clarifying_questions.append(
            ClarificationQuestion(
                id="q1",
                question="What decision should this report support most directly?",
                rationale="The workflow needs a clear decision objective to prioritize recommendations.",
                priority="high",
            )
        )

    if not brief.time_horizon:
        clarifying_questions.append(
            ClarificationQuestion(
                id="q2",
                question="What time horizon should the recommendations prioritize: short term, medium term, or long term?",
                rationale="Time horizon changes the type of recommendations and implementation roadmap.",
                priority="high",
            )
        )

    if not brief.preferred_source_types:
        clarifying_questions.append(
            ClarificationQuestion(
                id="q3",
                question="Which source types should be prioritized: consulting reports, company filings, academic research, regulators, industry news, or market data?",
                rationale="Source preferences improve retrieval relevance and trustworthiness.",
                priority="medium",
            )
        )

    if not brief.kpis:
        clarifying_questions.append(
            ClarificationQuestion(
                id="q4",
                question="Which KPIs matter most for this case: margin, revenue growth, basket size, retention, same-store sales, inventory turnover, shrinkage, or another metric?",
                rationale="KPIs help align the analysis and final recommendation.",
                priority="medium",
            )
        )

    normalized_case_description = render_case_description(brief)

    is_ready = len(missing_critical_fields) == 0

    return IntakeAssessment(
        is_ready=is_ready,
        missing_critical_fields=missing_critical_fields,
        clarifying_questions=clarifying_questions,
        normalized_case_description=normalized_case_description,
    )