import os
import json
import csv
import sqlite3
from datetime import datetime

from experiment_config import RUN_LOG_DIR, METRICS_FILE, SQLITE_DB_PATH


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

    metrics = run_record.get("metrics", {}) or {}
    latency = run_record.get("latency_seconds", {}) or {}
    config = run_record.get("configuration", {}) or {}

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "run_id": run_record.get("run_id"),
        "case_id": run_record.get("case_id"),
        "architecture": run_record.get("architecture"),
        "success": run_record.get("success"),
        "delivery_status": run_record.get("delivery_status"),

        # 6 primary evaluation metrics
        "governance_score": metrics.get("governance_score"),
        "governance_score_llm": metrics.get("governance_score_llm"),
        "governance_score_composite": metrics.get("governance_score_composite"),
        "structural_quality_score": metrics.get("structural_quality_score"),
        "strategic_depth_index": metrics.get("strategic_depth_index"),
        "unsupported_claim_rate": metrics.get("unsupported_claim_rate"),
        "citation_coverage": metrics.get("citation_coverage"),
        "total_cost_usd": metrics.get("total_cost_usd"),
        "hallucination_detected": (run_record.get("governance_diagnostics", {}) or {}).get("hallucination_detected", False),

        # optional run context for experiments
        "total_latency": latency.get("total", 0),
        "total_tokens": metrics.get("total_tokens") or 0,
        "model_deployment": config.get("model", {}).get("deployment_name"),
        "model_temperature": config.get("model", {}).get("temperature"),
        "prompt_version": config.get("versioning", {}).get("prompt_version"),
        "workflow_version": config.get("versioning", {}).get("workflow_version"),
        "retrieval_provider": config.get("retrieval", {}).get("provider"),
        "retrieval_num_results": config.get("retrieval", {}).get("num_results"),
        "governance_threshold": config.get("policy", {}).get("governance_approval_threshold"),
        "json_retry_max_retries": config.get("policy", {}).get("json_retry_max_retries"),
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


def init_sqlite_db():
    os.makedirs(RUN_LOG_DIR, exist_ok=True)

    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            case_id TEXT,
            timestamp TEXT,
            architecture TEXT,
            success INTEGER,
            delivery_status TEXT,
            total_latency REAL,
            total_tokens INTEGER,
            total_cost_usd REAL,
            governance_score REAL,
            governance_score_llm REAL,
            governance_score_composite REAL,
            hallucination_detected INTEGER,
            configuration_json TEXT,
            consultant_brief_json TEXT,
            intake_assessment_json TEXT,
            retrieval_json TEXT,
            metrics_json TEXT,
            full_run_json TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            agent_name TEXT,
            latency REAL,
            tokens INTEGER,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            cost REAL,
            retry_count INTEGER,
            valid_output INTEGER,
            metadata_json TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
    """)

    conn.commit()
    conn.close()


def save_run_to_sqlite(run_record: dict):
    try:
        init_sqlite_db()

        metrics = run_record.get("metrics", {}) or {}
        latency = run_record.get("latency_seconds", {}) or {}
        configuration = run_record.get("configuration", {}) or {}

        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO runs (
                run_id,
                case_id,
                timestamp,
                architecture,
                success,
                delivery_status,
                total_latency,
                total_tokens,
                total_cost_usd,
                governance_score,
                governance_score_llm,
                governance_score_composite,
                hallucination_detected,
                configuration_json,
                consultant_brief_json,
                intake_assessment_json,
                retrieval_json,
                metrics_json,
                full_run_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_record.get("run_id"),
            run_record.get("case_id"),
            run_record.get("timestamp"),
            run_record.get("architecture"),
            int(bool(run_record.get("success"))),
            run_record.get("delivery_status"),
            latency.get("total"),
            metrics.get("total_tokens"),
            metrics.get("total_cost_usd"),
            metrics.get("governance_score"),
            metrics.get("governance_score_llm"),
            metrics.get("governance_score_composite"),
            int(bool((run_record.get("governance_diagnostics", {}) or {}).get("hallucination_detected"))),
            json.dumps(configuration, ensure_ascii=False),
            json.dumps(run_record.get("consultant_brief"), ensure_ascii=False),
            json.dumps(run_record.get("intake_assessment"), ensure_ascii=False),
            json.dumps(run_record.get("retrieval"), ensure_ascii=False),
            json.dumps(metrics, ensure_ascii=False),
            json.dumps(run_record, ensure_ascii=False),
        ))

        cur.execute("DELETE FROM agent_metrics WHERE run_id = ?", (run_record.get("run_id"),))

        for agent_name, meta in (run_record.get("agents", {}) or {}).items():
            cur.execute("""
                INSERT INTO agent_metrics (
                    run_id,
                    agent_name,
                    latency,
                    tokens,
                    prompt_tokens,
                    completion_tokens,
                    cost,
                    retry_count,
                    valid_output,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_record.get("run_id"),
                agent_name,
                meta.get("latency"),
                meta.get("tokens"),
                meta.get("prompt_tokens"),
                meta.get("completion_tokens"),
                meta.get("cost"),
                meta.get("retry_count"),
                int(bool(meta.get("valid_output"))),
                json.dumps(meta, ensure_ascii=False),
            ))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"[LOGGING ERROR] Could not save run to SQLite: {e}")
