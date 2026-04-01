import os


# ===== Version control =====
WORKFLOW_VERSION = "v1.0.0"
PROMPT_VERSION = "v1.0.0"
SCHEMA_VERSION = "v1.0.0"
INTAKE_VERSION = "v1.0.0"
RETRIEVAL_VERSION = "v1.0.0"
GOVERNANCE_VERSION = "v1.0.0"


# ===== Model / DSPy config =====
MODEL_PROVIDER = "azure_openai_via_dspy"
MODEL_DEPLOYMENT = (
    os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    or os.getenv("AZURE_OPENAI_DEPLOYMENT")
    or "unknown"
)
MODEL_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
MODEL_TEMPERATURE = 0
DSPY_TRACK_USAGE = True


# ===== Workflow / policy config =====
ARCHITECTURE_DEFAULT = "multi_agent_4_dspy"
USE_EXTERNAL_RAG_DEFAULT = True
GOVERNANCE_APPROVAL_THRESHOLD = 0.80
JSON_RETRY_MAX_RETRIES = 3


# ===== Retrieval config =====
RETRIEVAL_PROVIDER = "serper"
RETRIEVAL_NUM_RESULTS = 8
RETRIEVAL_TOP_K = 5
RETRIEVAL_CACHE_ENABLED = True
RETRIEVAL_TIMEOUT_SECONDS = 30
PAGE_FETCH_TIMEOUT_SECONDS = 20
PAGE_FETCH_MAX_CHARS = 6000


# ===== Logging config =====
RUN_LOG_DIR = "run_logs"
METRICS_FILE = "metrics.csv"
SQLITE_DB_PATH = os.path.join(RUN_LOG_DIR, "aiops_runs.db")