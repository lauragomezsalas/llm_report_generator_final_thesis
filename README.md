# 🚀 Strategic Consulting Copilot

A multi-agent AI system that generates **consulting-grade strategic reports** using DSPy, RAG, and governance evaluation.

---

## 🔧 Features

- 🧠 Multi-agent architecture (Problem structuring → Analysis → Report → Governance)
- 📊 Retrieval-Augmented Generation (RAG) with external evidence and APA citations
- 🧪 DSPy-based structured prompting with JSON validation + retry
- 🛡️ Governance layer detecting hallucinations and unsupported claims
- 📈 Evaluation metrics (strategic depth, citation coverage, etc.)
- 🖥️ Streamlit UI with human-in-the-loop iteration
- 📄 DOCX export of consulting-style reports

---

## 🏗️ Architecture

Intake → Problem Structuring → Retrieval (RAG) → Strategic Analysis → Report Generation → Governance

---

## ⚙️ Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=...
SERPER_API_KEY=...
```

---

## ▶️ Run

CLI:
```bash
python main.py
```

Streamlit:
```bash
streamlit run streamlit_app.py
```

---

## 🧠 Key Idea

Simulates a consulting team where each agent performs a structured task and outputs are validated before delivery.

---

## ⚠️ Limitations

- Requires external APIs
- Dependent on retrieval quality
- Some modules simplified for portability

---

## 📌 Future Improvements

- Stronger citation grounding
- Better governance calibration
- Full experiment tracking
