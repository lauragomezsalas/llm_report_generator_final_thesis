import dspy


class ProblemStructuringSignature(dspy.Signature):
    """
    Diagnose a retail strategy case and return ONLY valid JSON matching:
    {
      "company_analysis": str,
      "market_analysis": str,
      "key_challenges": [str],
      "areas_of_improvement": [str],
      "kpis": [str],
      "strategic_questions": [str]
    }
    """
    case_description = dspy.InputField()
    json_output = dspy.OutputField()


class StrategicAnalysisSignature(dspy.Signature):
    """
    Analyze strategic alternatives using diagnosis and evidence.

    STRICT RULES:
    - Do NOT invent numerical estimates unless supported by evidence.
    - If no evidence exists, explicitly state: "no reliable estimate available".
    - Avoid generic reasoning without grounding in the provided evidence.
    - Every strategic claim must be linked to at least one evidence_id.
    - Do NOT rely on general business knowledge if it is not present in the evidence bundle.
    - If external evidence is provided, every alternative MUST contain at least one evidence_id.
    - If an alternative has an empty evidence_ids list while evidence exists, the output is INVALID.
    - Do NOT produce generic alternatives with evidence_ids = [] when evidence is available.

    QUALITY REQUIREMENTS:
    - Each alternative must clearly explain:
        - WHY it addresses the identified challenges
        - WHAT impact it has (grounded in evidence)
        - WHAT risks exist (realistic, not generic)
    - Trade-off analysis must compare alternatives explicitly (not just describe them)
    - Prioritization must be justified using criteria (e.g. margin impact, feasibility, risk)

    Return ONLY valid JSON matching:
    {
      "strategic_alternatives": [
        {
          "id": str,
          "title": str,
          "strategic_rationale": str,
          "expected_impact_summary": str,
          "risk_summary": str,
          "priority_score": float | null,
          "evidence_ids": [str]
        }
      ],
      "trade_off_analysis": str,
      "prioritization_logic": str,
      "recommended_option": str
    }
    """
    case_description = dspy.InputField()
    problem_structuring_output = dspy.InputField()
    external_evidence = dspy.InputField()
    json_output = dspy.OutputField()


class ReportGenerationSignature(dspy.Signature):
    """
    Write a consulting-style report and return ONLY valid JSON.

    CRITICAL RULES:
    - EVERY claim MUST be supported by at least one evidence_id.
    - If a claim is not supported by the evidence bundle, DO NOT include it.
    - Do NOT make generic consulting statements without grounding.
    - Avoid vague statements like "improves margins" unless supported by evidence.
    - If evidence is weak or missing, explicitly say so.
    - If external evidence exists, each strategic alternative section MUST include non-empty evidence_ids.
    - If external evidence exists, each strategic alternative section MUST include at least one APA citation.
    - The references section MUST be populated from the evidence bundle when evidence exists.
    - If evidence exists but citations are missing, the output is INVALID.

    REQUIRED OUTPUT SCHEMA:
    {
      "executive_summary": str,
      "key_insights": [str],
      "company_and_market_overview": str,
      "strategic_alternatives_section": [
        {
          "id": str,
          "title": str,
          "strategic_rationale": str,
          "expected_impact_summary": str,
          "risk_summary": str,
          "evidence_ids": [str],
          "apa_citations": [str]
        }
      ],
      "trade_off_discussion": str,
      "financial_impact_summary": [
        {
          "metric": str,
          "estimate": str,
          "rationale": str,
          "apa_citations": [str]
        }
      ],
      "final_recommendation": {
        "selected_alternative": str,
        "justification": str,
        "implementation_roadmap_summary": str,
        "evidence_ids": [str],
        "apa_citations": [str]
      },
      "implementation_timeline": [
        {
          "phase_title": str,
          "timeline": str,
          "objectives": [str],
          "key_actions": [str],
          "expected_outputs": [str]
        }
      ],
      "risks_and_mitigation": [
        {
          "risk": str,
          "mitigation": str,
          "severity": str,
          "apa_citations": [str]
        }
      ],
      "conclusion": str,
      "references": [str]
    }

    IMPORTANT:
    - DO NOT use fields like "phase" or "description" inside implementation_timeline.
    - implementation_timeline items MUST use exactly:
      phase_title, timeline, objectives, key_actions, expected_outputs
    - financial_impact_summary items MUST use apa_citations, not citation.
    - strategic_alternatives_section items MUST include apa_citations.
    - final_recommendation MUST include evidence_ids and apa_citations.
    - risks_and_mitigation items MUST include apa_citations.

    Return ONLY valid JSON.
    """
    problem_structuring_output = dspy.InputField()
    strategic_analysis_output = dspy.InputField()
    external_evidence = dspy.InputField()
    json_output = dspy.OutputField()


class GovernanceSignature(dspy.Signature):
    """
    Audit the outputs and return ONLY valid JSON matching:
    {
      "structural_validation": {
        "schema_compliance_score": float,
        "missing_fields": [str],
        "formatting_issues_detected": bool
      },
      "cross_agent_consistency": {
        "numerical_consistency_score": float,
        "inconsistencies_found": [str]
      },
      "logical_coherence": {
        "strategy_alignment_score": float,
        "diagnosis_alignment_score": float,
        "justification_consistency_score": float
      },
      "risk_evaluation": {
        "risk_realism_score": float,
        "confidence_calibration_score": float
      },
      "governance_flags": {
        "hallucination_detected": bool,
        "unsupported_claims": [str],
        "overconfidence_detected": bool
      },
      "overall_governance_score": float
    }

    IMPORTANT SCORING RULES:
    - All scores MUST be on a 0-10 scale, where:
      0-2 = very poor
      3-4 = weak
      5-6 = acceptable
      7-8 = strong
      9 = excellent
      10 = exceptional and extremely rare
    - Do NOT give 10 unless the output is near flawless and strongly evidenced.
    - Do NOT give 9 or 10 if there are unsupported claims, vague reasoning, weak trade-off logic,
      missing citations, generic recommendations, or weak alignment across stages.
    - Be conservative and critical.
    - If evidence is missing, reduce scores.
    - If the report contains generic business advice not clearly grounded in the evidence bundle,
      add those items to unsupported_claims.
    - If the final recommendation is not strongly justified from diagnosis + alternatives,
      reduce justification_consistency_score.
    - overall_governance_score must reflect the weaknesses found and should not exceed the weakest
      major dimension by a large margin.
    """
    problem_structuring_output = dspy.InputField()
    strategic_analysis_output = dspy.InputField()
    report_output = dspy.InputField()
    external_evidence = dspy.InputField()
    json_output = dspy.OutputField()


class ProblemStructuringModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.program = dspy.ChainOfThought(ProblemStructuringSignature)

    async def aforward(self, case_description: str):
        return await self.program.acall(case_description=case_description)


class StrategicAnalysisModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.program = dspy.ChainOfThought(StrategicAnalysisSignature)

    async def aforward(
        self,
        case_description: str,
        problem_structuring_output: str,
        external_evidence: str,
    ):
        return await self.program.acall(
            case_description=case_description,
            problem_structuring_output=problem_structuring_output,
            external_evidence=external_evidence,
        )


class ReportGenerationModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.program = dspy.ChainOfThought(ReportGenerationSignature)

    async def aforward(
        self,
        problem_structuring_output: str,
        strategic_analysis_output: str,
        external_evidence: str,
    ):
        return await self.program.acall(
            problem_structuring_output=problem_structuring_output,
            strategic_analysis_output=strategic_analysis_output,
            external_evidence=external_evidence,
        )


class GovernanceModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.program = dspy.ChainOfThought(GovernanceSignature)

    async def aforward(
        self,
        problem_structuring_output: str,
        strategic_analysis_output: str,
        report_output: str,
        external_evidence: str,
    ):
        return await self.program.acall(
            problem_structuring_output=problem_structuring_output,
            strategic_analysis_output=strategic_analysis_output,
            report_output=report_output,
            external_evidence=external_evidence,
        )