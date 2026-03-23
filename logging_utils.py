import os
import json
import csv
from datetime import datetime


RUN_LOG_DIR = "run_logs"
METRICS_FILE = "metrics.csv"

os.makedirs(RUN_LOG_DIR, exist_ok=True)


def save_full_run(run_record: dict):
    """
    Save full run record as JSON file.
    """

    run_id = run_record.get("run_id", "unknown_run")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    filename = f"{run_id}_{timestamp}.json"
    filepath = os.path.join(RUN_LOG_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(run_record, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[LOGGING ERROR] Could not save full run: {e}")


def append_metrics_row(run_record: dict):
    """
    Append summarized metrics to CSV file.
    """

    filepath = os.path.join(RUN_LOG_DIR, METRICS_FILE)

    # --- Safe extraction ---
    metrics = run_record.get("metrics", {}) or {}
    latency = run_record.get("latency_seconds", {}) or {}

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "run_id": run_record.get("run_id"),
        "case_id": run_record.get("case_id"),
        "architecture": run_record.get("architecture"),
        "success": run_record.get("success"),

        # NEW important field
        "delivery_status": run_record.get("delivery_status"),

        # latency
        "total_latency": latency.get("total", 0),

        # metrics (safe defaults)
        "total_tokens": metrics.get("total_tokens") or 0,
        "total_cost_usd": metrics.get("total_cost_usd") or 0,
        "governance_score": metrics.get("governance_score") or 0,
        "hallucination_detected": metrics.get("hallucination_detected", False),
    }

    file_exists = os.path.isfile(filepath)

    try:
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)

    except Exception as e:
        print(f"[LOGGING ERROR] Could not append metrics row: {e}")
