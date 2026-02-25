# 🛒 Multi-Agent LLM for Strategic Consultancy Reports (Grocery Retail)

## 📌 Overview

This project implements a **multi-agent Large Language Model (LLM) system** that automatically generates strategic consultancy reports for the grocery retail sector.

The system combines:

- **Multi-agent task decomposition**
- **Structured prompt orchestration**
- **Retrieval-Augmented Generation (RAG)**
- **Governance agent for quality control**
- **Token and cost tracking for evaluation**

It supports the empirical analysis of whether AI-generated reports can match or exceed manually developed reports in quality and cost-efficiency.

---

## 🏗️ Architecture

The pipeline consists of four stages:

1. **Problem Structuring Agent** – Converts case input into structured business analysis.  
2. **Strategic Analysis Agent** – Generates alternatives and trade-off evaluation.  
3. **Report Generation Agent** – Produces a consultancy-style report.  
4. **Governance Agent** – Evaluates consistency, groundedness, and structural compliance.  

An **Orchestrator** coordinates execution and logs latency, token usage, and estimated cost.

---

## 📂 Project Structure

```
├── main.py
├── orchestrator.py
├── problem_structuring.py
├── strategic_analysis.py
├── report_generation.py
├── governance_agent.py
├── retrieval_external.py
├── logging_utils.py
├── run_display.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Tech Stack

- Python  
- OpenAI Python SDK (Azure OpenAI configuration)  
- Embedding-based retrieval  
- JSON-structured prompting  
- Experiment logging (JSON + CSV)

---

## 🚀 Installation

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
pip install -r requirements.txt
```

Create a `.env` file:

```
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

---

## ▶️ Run

```bash
python main.py
```

This executes the full pipeline, generates a report, runs governance checks, and logs performance metrics.

---

## 📊 Evaluation Focus

The system is evaluated on:

- **Analytical quality**
- **Factual groundedness**
- **Robustness**
- **Cost-efficiency**

It supports baseline comparison and architectural ablation testing.

---

## 🏢 Business Relevance

Designed for integration into consulting workflows to:

- Reduce drafting time  
- Improve structural consistency  
- Enhance transparency through governance  
- Optimize cost–performance trade-offs  

---

**Final Thesis – Business & Data Analytics**
