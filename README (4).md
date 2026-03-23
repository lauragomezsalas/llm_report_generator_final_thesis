# Retail Consulting Multi-Agent Workflow

A modular **multi-agent strategic consulting system** built in Python using the **Microsoft Agent Framework**, **Azure OpenAI**, and an external **retrieval layer (RAG)** powered by Serper and web scraping.

The system simulates a consulting-style workflow in which multiple specialized agents collaborate to:

- structure a business problem,
- retrieve external evidence,
- evaluate strategic alternatives,
- generate an executive-style report, and
- audit the final output through a governance layer.

It also supports:

- **run logging**,
- **metrics tracking**,
- **console summaries**, and
- **DOCX export** for downloadable reports.

---

## Features

### Multi-agent architecture
The workflow is split into four specialized agents:

1. **Problem Structuring Agent**  
   Diagnoses the company situation, market context, challenges, improvement areas, KPIs, and strategic questions.

2. **Strategic Analysis Agent**  
   Generates and compares strategic alternatives using retrieved external evidence.

3. **Report Generation Agent**  
   Produces a consulting-style final report in structured JSON format.

4. **Governance Audit Agent**  
   Validates consistency, realism, schema compliance, and grounding quality before export.

### External retrieval layer (RAG)
The retrieval component:

- builds a search query from the problem-structuring output,
- calls the **Serper API**,
- extracts text from web pages,
- ranks documents by relevance,
- assigns `evidence_id` references, and
- generates APA-style citation fields.

### Reporting and export
The project includes:

- detailed console run summaries,
- JSON run logging,
- CSV metrics logging, and
- automatic **Word report export** via `python-docx`.

---

## Project structure

```text
.
├── agents_config.py          # Agent definitions and instructions
├── config.py                 # Environment loading and Azure client setup
├── enhanced_run_display.py   # Console summary and output preview
├── export_report_docx.py     # Word report generation
├── logging_utils.py          # JSON + CSV run logging
├── main.py                   # Entry point / demo execution
├── requirements.txt          # Python dependencies
├── retrieval.py              # External retrieval and evidence building
├── schemas.py                # Pydantic schemas for all agent outputs
├── workflow.py               # End-to-end workflow orchestration
├── .env                      # Local secrets only (DO NOT upload)
├── retrieval_cache/          # Cached retrieval responses
├── run_logs/                 # Saved run records and metrics
└── generated_reports/        # Exported .docx reports
```

---

## How it works

The workflow follows this sequence:

```text
Case description
   -> Problem Structuring Agent
   -> Retrieval Layer (optional external RAG)
   -> Strategic Analysis Agent
   -> Report Generation Agent
   -> Governance Audit Agent
   -> Logging + DOCX export
```

Each stage passes structured JSON to the next one, which makes the system easier to debug, validate, and extend.

---

## Requirements

- Python 3.10+
- Azure OpenAI deployment
- Serper API key

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## Environment variables

Create a local `.env` file with:

```env
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=your_deployment_name_here
AZURE_OPENAI_API_VERSION=2024-10-21
SERPER_API_KEY=your_serper_key_here
```

> **Important:** Never upload your real `.env` file to GitHub.

---

## Running the project

Run the main script:

```bash
python main.py
```

This will:

1. run the full consulting workflow,
2. print a detailed run summary in the console,
3. save the full run record as JSON,
4. append metrics to a CSV log,
5. generate a DOCX report when possible.

---

## Outputs

### Console output
`enhanced_run_display.py` prints:

- run metadata,
- per-agent execution details,
- summarized agent outputs,
- retrieval details,
- metrics,
- latency breakdown,
- error traceback when relevant.

### Logged files
The workflow saves:

- full JSON run records in `run_logs/`
- aggregate metrics in `run_logs/metrics.csv`

### Generated reports
DOCX reports are saved to:

```text
generated_reports/
```

If governance passes the threshold, the report is exported as client-ready. Otherwise, it is marked for internal review.

---

## Core files

### `workflow.py`
Contains the orchestration logic for the full pipeline, including:

- workflow construction,
- structured agent execution,
- retrieval integration,
- token and cost aggregation,
- governance-based delivery decisions,
- run logging.

### `retrieval.py`
Implements the external evidence pipeline:

- query generation,
- Serper search,
- content extraction,
- relevance scoring,
- APA citation construction,
- retrieval caching.

### `schemas.py`
Defines all Pydantic schemas used across the pipeline to enforce structured outputs and cross-agent consistency.

### `export_report_docx.py`
Builds a formatted Word report from the final run record.

---

## Example use case

The current demo in `main.py` uses a case about a **mid-sized supermarket chain in Spain** facing declining margins, stronger discount competition, and supply chain inefficiencies.

The workflow can be adapted to other strategic consulting cases by changing the case description input.

---

## What should be uploaded to GitHub

### Upload these files

- `agents_config.py`
- `config.py`
- `enhanced_run_display.py`
- `export_report_docx.py`
- `logging_utils.py`
- `main.py`
- `requirements.txt`
- `retrieval.py`
- `schemas.py`
- `workflow.py`
- `README.md`
- `.gitignore`

### Do **not** upload these

- `.env`
- `__pycache__/`
- `.venv/` or `venv/`
- `retrieval_cache/`
- `run_logs/`
- `generated_reports/`
- any files containing real API keys, tokens, or credentials

---

## Suggested `.gitignore`

```gitignore
# Secrets
.env
*.env

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# Virtual environments
.venv/
venv/
env/

# Project outputs
retrieval_cache/
run_logs/
generated_reports/

# OS / editor files
.DS_Store
Thumbs.db
.vscode/
.idea/
```

---

## Security note

This project depends on private API credentials loaded through environment variables in `config.py`. Those credentials must stay local and must never be committed to a public repository.

If a real `.env` file has already been exposed, the keys should be **rotated immediately**.

---

## Possible future improvements

Some natural next steps for the project are:

- stronger source filtering and ranking,
- more robust HTML extraction,
- improved citation validation,
- retry/error handling for failed agent calls,
- unit tests for schemas and workflow steps,
- support for batch case execution,
- a Streamlit or web interface.

---

## License

Add your preferred license here, for example:

- MIT License
- Apache 2.0
- Proprietary / academic use only

If you have not chosen one yet, leave this section and add it before publishing.
