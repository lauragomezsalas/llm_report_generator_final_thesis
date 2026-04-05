from pydantic import BaseModel, Field
from typing import List, Optional

from pydantic import BaseModel, Field
from typing import List, Optional


class ConsultantBrief(BaseModel):
    company_name: str
    geography: str
    sector: str = "grocery retail"
    sub_sector: Optional[str] = None
    business_model: Optional[str] = None
    company_size: Optional[str] = None

    main_problem: str
    symptoms: List[str] = Field(default_factory=list)
    suspected_root_causes: List[str] = Field(default_factory=list)

    objectives: List[str] = Field(default_factory=list)
    key_questions: List[str] = Field(default_factory=list)
    kpis: List[str] = Field(default_factory=list)

    time_horizon: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    strategic_priorities: List[str] = Field(default_factory=list)

    preferred_source_types: List[str] = Field(default_factory=list)
    preferred_domains: List[str] = Field(default_factory=list)
    banned_domains: List[str] = Field(default_factory=list)
    recency_preference: Optional[str] = None

    preferred_report_style: Optional[str] = None
    preferred_report_length: Optional[str] = None
    extra_context: Optional[str] = None


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    rationale: str
    priority: str


class IntakeAssessment(BaseModel):
    is_ready: bool
    missing_critical_fields: List[str] = Field(default_factory=list)
    clarifying_questions: List[ClarificationQuestion] = Field(default_factory=list)
    normalized_case_description: str


class ProblemStructuringOutput(BaseModel):
    company_analysis: str
    market_analysis: str
    key_challenges: List[str] = Field(default_factory=list)
    areas_of_improvement: List[str] = Field(default_factory=list)
    kpis: List[str] = Field(default_factory=list)
    strategic_questions: List[str] = Field(default_factory=list)


class StrategicAlternative(BaseModel):
    id: str
    title: str
    strategic_rationale: str
    expected_impact_summary: str
    risk_summary: str
    priority_score: Optional[float] = None
    evidence_ids: List[str] = Field(default_factory=list)


class StrategicAnalysisOutput(BaseModel):
    strategic_alternatives: List[StrategicAlternative] = Field(default_factory=list)
    trade_off_analysis: str
    prioritization_logic: str
    recommended_option: str


class ReportAlternativeSection(BaseModel):
    id: str
    title: str
    strategic_rationale: str
    expected_impact_summary: str
    risk_summary: str
    evidence_ids: List[str] = Field(default_factory=list)
    apa_citations: List[str] = Field(default_factory=list)


class FinancialImpactItem(BaseModel):
    metric: str
    estimate: str
    rationale: str
    apa_citations: List[str] = Field(default_factory=list)


class ImplementationPhase(BaseModel):
    phase_title: str
    timeline: str
    objectives: List[str] = Field(default_factory=list)
    key_actions: List[str] = Field(default_factory=list)
    expected_outputs: List[str] = Field(default_factory=list)


class RiskMitigationItem(BaseModel):
    risk: str
    mitigation: str
    severity: str
    apa_citations: List[str] = Field(default_factory=list)


class FinalRecommendation(BaseModel):
    selected_alternative: str
    justification: str
    implementation_roadmap_summary: str
    evidence_ids: List[str] = Field(default_factory=list)
    apa_citations: List[str] = Field(default_factory=list)


class ReportOutput(BaseModel):
    executive_summary: str
    key_insights: List[str] = Field(default_factory=list)
    company_and_market_overview: str
    strategic_alternatives_section: List[ReportAlternativeSection] = Field(default_factory=list)
    trade_off_discussion: str
    financial_impact_summary: List[FinancialImpactItem] = Field(default_factory=list)
    final_recommendation: FinalRecommendation
    implementation_timeline: List[ImplementationPhase] = Field(default_factory=list)
    risks_and_mitigation: List[RiskMitigationItem] = Field(default_factory=list)
    conclusion: str
    references: List[str] = Field(default_factory=list)


class StructuralValidation(BaseModel):
    schema_compliance_score: float  # 0-10
    missing_fields: List[str] = Field(default_factory=list)
    formatting_issues_detected: bool


class CrossAgentConsistency(BaseModel):
    numerical_consistency_score: float  # 0-10
    inconsistencies_found: List[str] = Field(default_factory=list)


class LogicalCoherence(BaseModel):
    strategy_alignment_score: float  # 0-10
    diagnosis_alignment_score: float  # 0-10
    justification_consistency_score: float  # 0-10


class RiskEvaluation(BaseModel):
    risk_realism_score: float  # 0-10
    confidence_calibration_score: float  # 0-10


class GovernanceFlags(BaseModel):
    hallucination_detected: bool
    unsupported_claims: List[str] = Field(default_factory=list)
    overconfidence_detected: bool


class GovernanceOutput(BaseModel):
    structural_validation: StructuralValidation
    cross_agent_consistency: CrossAgentConsistency
    logical_coherence: LogicalCoherence
    risk_evaluation: RiskEvaluation
    governance_flags: GovernanceFlags
    overall_governance_score: float  # 0-10