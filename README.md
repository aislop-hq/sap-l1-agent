# SAP Basis L1 Support Agent

Multi-agent system that diagnoses SAP Basis incidents via SSH + sapcontrol
and proposes (or executes with human approval) remediation actions.

Built with Python, LangGraph, OpenAI GPT-4o, Qdrant, Langfuse, and FastAPI.

## Quick Start (Demo Mode)

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
DEMO_MODE=true python run_agent.py --scenario 1
```

No real SAP system, OpenAI key, or Qdrant needed in demo mode.

## Demo Scenarios

```bash
DEMO_MODE=true python run_agent.py --scenario 1   # Hung Work Process (approval required)
DEMO_MODE=true python run_agent.py --scenario 2   # Filesystem Critical (approval required)
DEMO_MODE=true python run_agent.py --scenario 3   # ABAP Dump (informational, autonomous)
DEMO_MODE=true python run_agent.py --scenario 4   # Instance Down (escalation, autonomous)
```

Or use explicit arguments:
```bash
DEMO_MODE=true python run_agent.py --host mock --sid DEV --nr 00 --alert "WP02 not responding"
```

## Full Setup (RAG + Langfuse + Real Mode)

### 1. Start Qdrant

```bash
docker compose up -d
```

This starts Qdrant on `http://localhost:6333`.

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in your `.env`:

| Variable | Required for | Notes                                                              |
|----------|-------------|--------------------------------------------------------------------|
| `OPENAI_API_KEY` | RAG + RCA | Used for embeddings and GPT-4o synthesis                           |
| `OPENAI_BASE_URL` | RAG + RCA | https://api.openai.com/v1 or custom model endpoint                 |
| `OPENAI_MODEL` | RAG + RCA | OpenAI model to use 'gpt-4o-mini'                                               |
| `QDRANT_URL` | RAG | Default: `http://localhost:6333`                                   |
| `LANGFUSE_PUBLIC_KEY` | Tracing | Get from [Langfuse Cloud](https://cloud.langfuse.com) or self-host |
| `LANGFUSE_SECRET_KEY` | Tracing | Same as above                                                      |
| `LANGFUSE_HOST` | Tracing | Default: `https://cloud.langfuse.com`                              |
| `SSH_DEFAULT_USER` | Real SSH | SAP admin user (e.g., `devadm`)                                    |
| `SSH_KEY_PATH` | Real SSH | Path to SSH private key                                            |
| `DEMO_MODE` | — | `true` for mock, `false` for real                                  |

### 3. Ingest runbooks into Qdrant

Preview what will be ingested:
```bash
python rag/ingest.py --dry-run
```

Run the real ingest (requires `OPENAI_API_KEY`):
```bash
python rag/ingest.py
```

This embeds 9 runbooks (70 chunks) into Qdrant using `text-embedding-3-small`.

### 4. Run with real RAG (still using mock SSH)

```bash
DEMO_MODE=true python run_agent.py --scenario 1
```

Even in demo mode, if Qdrant is running and populated, the RAG tool will
return real similarity search results instead of hardcoded ones — set
`DEMO_MODE=false` to use the LLM for RCA synthesis too.

### 5. Run fully real (requires SSH access to SAP host)

```bash
DEMO_MODE=false python run_agent.py \
  --host sap-prod-01 --sid PRD --nr 00 \
  --alert "WP02 not responding"
```

## Langfuse Tracing

When `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set:

- Each agent run creates a Langfuse trace named by the thread ID
- Spans: `supervisor_route`, `rca_diagnosis`, `remediation`, `report_generation`
- Operator approval decisions are logged as a Langfuse score (`operator_approval`: 1 or 0)

When credentials are not set, tracing is silently disabled with no warnings.

## Runbooks

9 SAP Basis runbooks in `rag/runbooks/`:

| Runbook | Keywords | Risk |
|---------|----------|------|
| Hung Work Process | WP, STOPPED, SIGSEGV | LOW |
| Filesystem Full | disk, cleanup, traces | MEDIUM |
| ABAP Dump (TIME_OUT) | dump, long-running SELECT | LOW |
| Instance Down | GRAY, dispatcher, outage | HIGH |
| Enqueue Lock Issues | SM12, lock table | MEDIUM |
| Update Process Failure | SM13, UPD, V1/V2 | MEDIUM |
| Memory Issues | PRIV, heap, OOM | MEDIUM |
| ICM / Web Dispatcher | HTTP, Fiori, SMICM | MEDIUM |
| Batch Job Failure | SM37, BTC, scheduled | LOW |

Add your own runbooks as markdown files with YAML front-matter, then re-run
`python rag/ingest.py`.

## FastAPI Webhook

```bash
python webhook.py
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/alert` | POST | Start incident analysis |
| `/status/{thread_id}` | GET | Get current state |
| `/approve/{thread_id}` | POST | Resume with approval decision |

```bash
# Create alert
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d '{"host": "mock", "sid": "DEV", "nr": "00", "alert": "WP02 not responding"}'

# Check status
curl http://localhost:8000/status/<thread_id>

# Approve
curl -X POST http://localhost:8000/approve/<thread_id> \
  -H "Content-Type: application/json" \
  -d '{"decision": "yes"}'
```
