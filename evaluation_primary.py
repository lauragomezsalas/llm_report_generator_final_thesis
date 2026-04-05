import re
from typing import Any


SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.!?])\s+')
CITATION_REGEX = re.compile(r'\(([^()]+?,\s*(?:19|20)\d{2}|[^()]+?,\s*n\.d\.)\)')


def safe_div(num: float, den: float) -> float:
    if den == 0:
        return 0.0
    return round(num / den, 4)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, round(x, 4)))


def normalize_0_10_to_0_1(x: float | int | None) -> float:
    if x is None:
        return 0.0
    return clamp01(float(x) / 10.0)


def split_into_statements(text: str) -> list[str]:
    if not text:
        return []
    text = str(text).strip()
    if not text:
        return []
    return [p.strip() for p in SENTENCE_SPLIT_REGEX.split(text) if p.strip()]


def text_has_citation(text: str) -> bool:
    if not text:
        return False
    return bool(CITATION_REGEX.search(text))


def list_has_content(values: list[Any] | None) -> bool:
    return bool(values and any(str(v).strip() for v in values))


def json_safe_dump(value: Any) -> str:
    try:
        import json
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def flatten_report_claims(report: dict) -> list[dict]:
    claims = []

    def add_text_claims(section: str, text: str, citation_list: list[str] | None = None):
        for stmt in split_into_statements(text):
            claims.append(
                {
                    "section": section,
                    "text": stmt,
                    "has_citation": bool(citation_list) or text_has_citation(stmt),
                }
            )

    add_text_claims("executive_summary", report.get("executive_summary", ""))

    for item in report.get("key_insights", []) or []:
        claims.append(
            {
                "section": "key_insights",
                "text": str(item),
                "has_citation": text_has_citation(str(item)),
            }
        )

    add_text_claims("company_and_market_overview", report.get("company_and_market_overview", ""))

    for alt in report.get("strategic_alternatives_section", []) or []:
        alt_citations = alt.get("apa_citations", []) or []
        add_text_claims("alternative_rationale", alt.get("strategic_rationale", ""), alt_citations)
        add_text_claims("alternative_impact", alt.get("expected_impact_summary", ""), alt_citations)
        add_text_claims("alternative_risk", alt.get("risk_summary", ""), alt_citations)

    add_text_claims("trade_off_discussion", report.get("trade_off_discussion", ""))

    for item in report.get("financial_impact_summary", []) or []:
        add_text_claims("financial_rationale", item.get("rationale", ""), item.get("apa_citations", []))
        estimate = item.get("estimate", "")
        if str(estimate).strip():
            claims.append(
                {
                    "section": "financial_estimate",
                    "text": str(estimate),
                    "has_citation": bool(item.get("apa_citations", [])),
                }
            )

    final_rec = report.get("final_recommendation", {}) or {}
    final_citations = final_rec.get("apa_citations", []) or []
    add_text_claims("final_justification", final_rec.get("justification", ""), final_citations)
    add_text_claims("roadmap_summary", final_rec.get("implementation_roadmap_summary", ""), final_citations)

    for risk_item in report.get("risks_and_mitigation", []) or []:
        claims.append(
            {
                "section": "risk",
                "text": str(risk_item.get("risk", "")),
                "has_citation": bool(risk_item.get("apa_citations", [])),
            }
        )
        claims.append(
            {
                "section": "mitigation",
                "text": str(risk_item.get("mitigation", "")),
                "has_citation": bool(risk_item.get("apa_citations", [])),
            }
        )

    add_text_claims("conclusion", report.get("conclusion", ""))

    return [c for c in claims if c["text"].strip()]


def compute_factual_groundedness(report: dict) -> dict:
    claims = flatten_report_claims(report)
    total_claims = len(claims)
    supported_claims = sum(1 for c in claims if c["has_citation"])
    unsupported_claims = total_claims - supported_claims

    return {
        "total_claims": total_claims,
        "supported_claims": supported_claims,
        "unsupported_claims": unsupported_claims,
        "unsupported_claim_rate": safe_div(unsupported_claims, total_claims),
        "citation_coverage": safe_div(supported_claims, total_claims),
    }


def compute_report_completeness_score(report: dict) -> float:
    checks = {
        "executive_summary": bool(str(report.get("executive_summary", "")).strip()),
        "key_insights": list_has_content(report.get("key_insights")),
        "company_and_market_overview": bool(str(report.get("company_and_market_overview", "")).strip()),
        "strategic_alternatives_section": list_has_content(report.get("strategic_alternatives_section")),
        "trade_off_discussion": bool(str(report.get("trade_off_discussion", "")).strip()),
        "financial_impact_summary": list_has_content(report.get("financial_impact_summary")),
        "final_recommendation": bool(report.get("final_recommendation")),
        "implementation_timeline": list_has_content(report.get("implementation_timeline")),
        "risks_and_mitigation": list_has_content(report.get("risks_and_mitigation")),
        "conclusion": bool(str(report.get("conclusion", "")).strip()),
        "references": list_has_content(report.get("references")),
    }

    present = sum(1 for v in checks.values() if v)
    total = len(checks)
    return safe_div(present, total)


def compute_kpi_alignment_score(problem_structuring_output: dict, report: dict) -> float:
    kpis = [str(k).lower().strip() for k in (problem_structuring_output.get("kpis", []) or []) if str(k).strip()]
    if not kpis:
        return 0.0

    report_text = " ".join([
        str(report.get("executive_summary", "")).lower(),
        str(report.get("company_and_market_overview", "")).lower(),
        str(report.get("trade_off_discussion", "")).lower(),
        str(report.get("conclusion", "")).lower(),
        json_safe_dump(report.get("financial_impact_summary", [])).lower(),
        json_safe_dump(report.get("final_recommendation", {})).lower(),
    ])

    hits = sum(1 for kpi in kpis if kpi in report_text)
    return safe_div(hits, len(kpis))


def compute_structural_quality_score(
    problem_structuring_output: dict,
    report: dict,
    governance_output: dict,
) -> float:
    structural_validation = governance_output.get("structural_validation", {}) or {}
    schema_component = normalize_0_10_to_0_1(structural_validation.get("schema_compliance_score"))
    completeness_component = compute_report_completeness_score(report)
    kpi_alignment_component = compute_kpi_alignment_score(problem_structuring_output, report)

    factual = compute_factual_groundedness(report)
    citation_component = factual["citation_coverage"]

    return round(
        (
            0.30 * schema_component
            + 0.30 * completeness_component
            + 0.20 * kpi_alignment_component
            + 0.20 * citation_component
        ),
        4
    )


def score_number_of_alternatives(n: int) -> float:
    if 3 <= n <= 5:
        return 1.0
    if n == 2 or n == 6:
        return 0.7
    if n == 1 or n == 7:
        return 0.4
    if n == 0:
        return 0.0
    return 0.2


def token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", str(text).lower()))


def jaccard_similarity(a: str, b: str) -> float:
    sa = token_set(a)
    sb = token_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def compute_alternative_diversity_score(alternatives: list[dict]) -> float:
    if len(alternatives) <= 1:
        return 0.0 if not alternatives else 0.5

    texts = []
    for alt in alternatives:
        texts.append(
            " ".join([
                str(alt.get("title", "")),
                str(alt.get("strategic_rationale", "")),
                str(alt.get("expected_impact_summary", "")),
                str(alt.get("risk_summary", "")),
            ])
        )

    sims = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            sims.append(jaccard_similarity(texts[i], texts[j]))

    mean_sim = sum(sims) / len(sims) if sims else 1.0
    return clamp01(1.0 - mean_sim)


def contains_numeric_content(text: str) -> bool:
    return bool(re.search(r"\b\d+(?:[\.,]\d+)?%?\b", str(text)))


def compute_quantification_completeness_score(alternatives: list[dict]) -> float:
    if not alternatives:
        return 0.0

    quantified = 0
    for alt in alternatives:
        if contains_numeric_content(alt.get("expected_impact_summary", "")):
            quantified += 1

    return safe_div(quantified, len(alternatives))


def compute_tradeoff_and_priority_score(
    strategic_analysis_output: dict,
    report: dict,
) -> float:
    text = " ".join([
        str(strategic_analysis_output.get("trade_off_analysis", "")),
        str(strategic_analysis_output.get("prioritization_logic", "")),
        str(report.get("trade_off_discussion", "")),
        str((report.get("final_recommendation", {}) or {}).get("justification", "")),
    ]).lower()

    components = [
        any(word in text for word in ["trade-off", "tradeoff", "compare", "comparison", "matrix"]),
        any(word in text for word in ["priority", "prioritize", "ranking", "ranked", "recommended"]),
        any(word in text for word in ["criteria", "weights", "logic", "justification"]),
        any(word in text for word in ["risk", "return", "impact", "cost", "margin"]),
    ]

    return round(sum(1 for x in components if x) / len(components), 4)


def compute_alignment_score(governance_output: dict) -> float:
    logical = governance_output.get("logical_coherence", {}) or {}

    strategy_alignment = normalize_0_10_to_0_1(logical.get("strategy_alignment_score"))
    diagnosis_alignment = normalize_0_10_to_0_1(logical.get("diagnosis_alignment_score"))
    justification_alignment = normalize_0_10_to_0_1(logical.get("justification_consistency_score"))

    return round(
        (strategy_alignment + diagnosis_alignment + justification_alignment) / 3.0,
        4
    )


def compute_strategic_depth_index(
    strategic_analysis_output: dict,
    report: dict,
    governance_output: dict,
) -> float:
    alternatives = strategic_analysis_output.get("strategic_alternatives", []) or []

    nas = score_number_of_alternatives(len(alternatives))
    ads = compute_alternative_diversity_score(alternatives)
    qcs = compute_quantification_completeness_score(alternatives)
    tradeoff_priority = compute_tradeoff_and_priority_score(strategic_analysis_output, report)
    alignment = compute_alignment_score(governance_output)

    return round((nas + ads + qcs + tradeoff_priority + alignment) / 5.0, 4)

def compute_composite_governance_score(
    llm_governance_score: float | None,
    structural_quality_score: float,
    strategic_depth_index: float,
    citation_coverage: float,
    unsupported_claim_rate: float,
) -> float:
    """
    Blend the independent LLM governance score with mathematical quality metrics.

    All inputs are on a 0-1 scale except unsupported_claim_rate,
    which is converted into a positive component as (1 - unsupported_claim_rate).
    """
    llm_component = clamp01(llm_governance_score or 0.0)
    structural_component = clamp01(structural_quality_score or 0.0)
    strategic_component = clamp01(strategic_depth_index or 0.0)
    citation_component = clamp01(citation_coverage or 0.0)
    support_component = clamp01(1.0 - (unsupported_claim_rate or 0.0))

    return round(
        (
            0.35 * llm_component
            + 0.25 * structural_component
            + 0.20 * strategic_component
            + 0.10 * citation_component
            + 0.10 * support_component
        ),
        4,
    )

def compute_primary_evaluation_metrics(payload: dict) -> dict:
    problem_structuring_output = payload.get("problem_structuring_output", {}) or {}
    strategic_analysis_output = payload.get("strategic_analysis_output", {}) or {}
    report = payload.get("report", {}) or {}
    governance_output = payload.get("governance_output", {}) or {}
    metrics = payload.get("metrics", {}) or {}

    factual = compute_factual_groundedness(report)

    structural_quality_score = compute_structural_quality_score(
        problem_structuring_output=problem_structuring_output,
        report=report,
        governance_output=governance_output,
    )

    strategic_depth_index = compute_strategic_depth_index(
        strategic_analysis_output=strategic_analysis_output,
        report=report,
        governance_output=governance_output,
    )

    llm_governance_score = metrics.get("governance_score_llm")

    composite_governance_score = compute_composite_governance_score(
        llm_governance_score=llm_governance_score,
        structural_quality_score=structural_quality_score,
        strategic_depth_index=strategic_depth_index,
        citation_coverage=factual["citation_coverage"],
        unsupported_claim_rate=factual["unsupported_claim_rate"],
    )

    return {
        "governance_score_llm": llm_governance_score,
        "governance_score_composite": composite_governance_score,
        "governance_score": composite_governance_score,
        "structural_quality_score": structural_quality_score,
        "strategic_depth_index": strategic_depth_index,
        "unsupported_claim_rate": factual["unsupported_claim_rate"],
        "citation_coverage": factual["citation_coverage"],
        "total_cost_usd": metrics.get("total_cost_usd"),
    }