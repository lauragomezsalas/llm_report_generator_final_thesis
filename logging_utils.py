import csv
import json
import os
from datetime import datetime

RESULTS_DIR = "experiment_results"
METRICS_FILE = os.path.join(RESULTS_DIR, "experiment_metrics.csv")

os.makedirs(RESULTS_DIR, exist_ok=True)


def save_full_run(run_record: dict):
    filename = os.path.join(
        RESULTS_DIR,
        f"{run_record['run_id']}.json"
    )
    with open(filename, "w") as f:
        json.dump(run_record, f, indent=2)


def append_metrics_row(run_record: dict):

    file_exists = os.path.isfile(METRICS_FILE)

    row = {
        "run_id": run_record["run_id"],
        "timestamp": run_record["timestamp"],
        "architecture": run_record["architecture"],
        "case_id": run_record["case_id"],
        "total_latency": run_record["latency_seconds"]["total"],
        "total_tokens": run_record.get("metrics", {}).get("total_tokens", 0),
        "total_cost": run_record.get("metrics", {}).get("total_cost", 0),
        "governance_score": run_record.get("metrics", {}).get("governance_score", 0),
        "hallucination_detected": run_record.get("metrics", {}).get("hallucination_detected", 0),
        "success": run_record["success"]
    }

    with open(METRICS_FILE, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=row.keys())

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)
