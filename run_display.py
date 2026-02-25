import json


def print_run_summary(run_record: dict):
    """
    Clean terminal visualization of a full pipeline run.
    Matches current orchestrator structure.
    """

    print("\n" + "=" * 70)
    print("RUN METADATA")
    print("=" * 70)
    print(f"Run ID: {run_record.get('run_id')}")
    print(f"Case ID: {run_record.get('case_id')}")
    print(f"Architecture: {run_record.get('architecture')}")
    print(f"External RAG: {run_record.get('use_external_rag')}")
    print(f"Success: {run_record.get('success')}")
    print(f"Total Latency: {run_record.get('latency_seconds', {}).get('total', 0):.3f}s")

    # ---------------- Agents ----------------
    print("\n" + "=" * 70)
    print("AGENT EXECUTION DETAILS")
    print("=" * 70)

    agents = run_record.get("agents", {})

    for agent_name in ["agent_1", "agent_2", "agent_3", "agent_4"]:
        if agent_name in agents:
            print("\n" + "-" * 50)
            print(agent_name.upper())
            print("-" * 50)
            print(json.dumps(agents.get(agent_name), indent=2))

    # ---------------- Retrieval ----------------
    if run_record.get("retrieval"):
        print("\n" + "=" * 70)
        print("RETRIEVAL LAYER")
        print("=" * 70)
        print(json.dumps(run_record.get("retrieval"), indent=2))

    # ---------------- Metrics ----------------
    print("\n" + "=" * 70)
    print("METRICS")
    print("=" * 70)
    print(json.dumps(run_record.get("metrics"), indent=2))

    # ---------------- Latency ----------------
    print("\n" + "=" * 70)
    print("LATENCY BREAKDOWN")
    print("=" * 70)
    print(json.dumps(run_record.get("latency_seconds"), indent=2))

    # ---------------- Error ----------------
    if not run_record.get("success"):
        print("\n" + "=" * 70)
        print("ERROR TRACEBACK")
        print("=" * 70)
        print(run_record.get("error"))

    print("\n" + "=" * 70)
    print("END OF RUN")
    print("=" * 70 + "\n")

