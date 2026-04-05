import json


def _truncate_text(text, max_chars=1200):
    if text is None:
        return ""

    text = str(text)
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n... [truncated]"


def _safe_pretty_json(data):
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except TypeError:
        return str(data)


def _summarize_output(data, max_chars=1200):
    if data is None:
        return "None"

    pretty = _safe_pretty_json(data)
    return _truncate_text(pretty, max_chars=max_chars)


def print_run_summary(run_record, show_agent_outputs=True, max_chars_per_output=1200):
    print("\n" + "=" * 70)
    print("RUN METADATA")
    print("=" * 70)
    print(f"Run ID: {run_record.get('run_id')}")
    print(f"Case ID: {run_record.get('case_id')}")
    print("Architecture:", run_record.get("architecture"))
    print("External RAG:", run_record.get("use_external_rag"))
    print("Success:", run_record.get("success"))
    print("Delivery Status:", run_record.get("delivery_status"))
    print("Total Latency:", run_record.get("latency_seconds", {}).get("total"))

    if run_record.get("consultant_brief"):
        print("\n" + "=" * 70)
        print("CONSULTANT BRIEF")
        print("=" * 70)
        print(_summarize_output(
            run_record.get("consultant_brief"),
            max_chars=max_chars_per_output
        ))

    if run_record.get("intake_assessment"):
        print("\n" + "=" * 70)
        print("INTAKE ASSESSMENT")
        print("=" * 70)
        print(_summarize_output(
            run_record.get("intake_assessment"),
            max_chars=max_chars_per_output
        ))

    if run_record.get("configuration"):
        print("\n" + "=" * 70)
        print("CONFIGURATION SNAPSHOT")
        print("=" * 70)
        print(_summarize_output(
            run_record.get("configuration"),
            max_chars=max_chars_per_output
        ))

    print("\n" + "=" * 70)
    print("AGENT EXECUTION DETAILS")
    print("=" * 70)

    for agent_name, info in run_record.get("agents", {}).items():
        print("\n" + "-" * 50)
        print(agent_name.upper())
        print("-" * 50)
        print(json.dumps(info, indent=2, ensure_ascii=False))

    if show_agent_outputs:
        outputs = [
            ("AGENT 1 OUTPUT - Problem Structuring", run_record.get("problem_structuring_output")),
            ("AGENT 2 OUTPUT - Strategic Analysis", run_record.get("strategic_analysis_output")),
            ("AGENT 3 OUTPUT - Final Report", run_record.get("report")),
            ("AGENT 4 OUTPUT - Governance", run_record.get("governance_output")),
        ]

        for title, data in outputs:
            print("\n" + "=" * 70)
            print(title)
            print("=" * 70)
            print(_summarize_output(data, max_chars=max_chars_per_output))

    if run_record.get("retrieval"):
        print("\n" + "=" * 70)
        print("RETRIEVAL LAYER")
        print("=" * 70)
        print(_summarize_output(run_record.get("retrieval"), max_chars=max_chars_per_output))

    print("\n" + "=" * 70)
    print("PRIMARY EVALUATION METRICS")
    print("=" * 70)

    primary_metrics = {
        "governance_score": (run_record.get("metrics", {}) or {}).get("governance_score"),
        "structural_quality_score": (run_record.get("metrics", {}) or {}).get("structural_quality_score"),
        "strategic_depth_index": (run_record.get("metrics", {}) or {}).get("strategic_depth_index"),
        "unsupported_claim_rate": (run_record.get("metrics", {}) or {}).get("unsupported_claim_rate"),
        "citation_coverage": (run_record.get("metrics", {}) or {}).get("citation_coverage"),
        "total_cost_usd": (run_record.get("metrics", {}) or {}).get("total_cost_usd"),
    }

    print(json.dumps(primary_metrics, indent=2, ensure_ascii=False))

    print("\n" + "=" * 70)
    print("LATENCY BREAKDOWN")
    print("=" * 70)
    print(json.dumps(run_record.get("latency_seconds", {}), indent=2, ensure_ascii=False))

    if not run_record.get("success"):
        print("\n" + "=" * 70)
        print("ERROR TRACEBACK")
        print("=" * 70)
        print(run_record.get("error"))

    print("\n" + "=" * 70)
    print("END OF RUN")
    print("=" * 70 + "\n")