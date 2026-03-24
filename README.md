# SAP Basis L1 Support Agent

Multi-agent system that diagnoses SAP Basis incidents via SSH + sapcontrol
and proposes (or executes with human approval) remediation actions.

Built with Python, LangGraph, OpenAI GPT-4o, Qdrant, Langfuse, and FastAPI.

## Quick Start (Demo Mode)

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
DEMO_MODE=true python run_agent.py --host mock --sid DEV --nr 00 --alert "WP02 not responding"
```

No real SAP system, OpenAI key, or Qdrant needed in demo mode.

## Demo Scenarios

### 1. Hung Work Process (requires approval)
```bash
python run_agent.py --host mock --sid DEV --nr 00 --alert "WP02 not responding"
```

### 2. Filesystem Critical (requires approval)
```bash
python run_agent.py --host mock --sid DEV --nr 00 --alert "filesystem critical on sap-dev-01"
```

### 3. ABAP Dump (informational — no approval)
```bash
python run_agent.py --host mock --sid DEV --nr 00 --alert "TIME_OUT dump in dev_w0"
```

### 4. Instance Down (escalation — no approval)
```bash
python run_agent.py --host mock --sid DEV --nr 00 --alert "instance not responding"
```

## FastAPI Webhook

```bash
python webhook.py
```

### Create an alert
```bash
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d '{"host": "mock", "sid": "DEV", "nr": "00", "alert": "WP02 not responding"}'
```

### Check status
```bash
curl http://localhost:8000/status/<thread_id>
```

### Approve remediation
```bash
curl -X POST http://localhost:8000/approve/<thread_id> \
  -H "Content-Type: application/json" \
  -d '{"decision": "yes"}'
```

## Real SSH Mode

1. Copy `.env.example` to `.env` and fill in real values:
   - `OPENAI_API_KEY` — required for LLM-based RCA synthesis
   - `SSH_DEFAULT_USER` / `SSH_KEY_PATH` — SSH credentials for the SAP host
   - `QDRANT_URL` — running Qdrant instance for RAG
   - `LANGFUSE_*` — optional, for tracing
2. Set `DEMO_MODE=false`
3. Ingest runbooks: `python rag/ingest.py`
4. Run: `python run_agent.py --host sap-prod-01 --sid PRD --nr 00 --alert "WP02 not responding"`
