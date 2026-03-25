"""FastAPI webhook entry point for the SAP L1 Support Agent.

Endpoints:
    POST /alert           — start a new incident analysis
    GET  /status/{id}     — get current graph state
    POST /approve/{id}    — resume a paused graph with approval decision
    GET  /                — health check
"""

from __future__ import annotations

import logging
import os
import uuid
from threading import Thread
from typing import Any

# Suppress Langfuse auth warnings before any @observe imports
import sys as _sys
from config import settings
if not settings.langfuse_public_key or not settings.langfuse_secret_key:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-stub")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-stub")
    os.environ.setdefault("LANGFUSE_HOST", "http://localhost:0")
    os.environ["LANGFUSE_ENABLED"] = "false"
    logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)

from fastapi import FastAPI, HTTPException  # noqa: E402
from langgraph.types import Command  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from langfuse_init import init_langfuse  # noqa: E402
from graph.graph import compiled_graph  # noqa: E402
from tools.ssh_tools import set_scenario  # noqa: E402

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(message)s",
)
init_langfuse()

app = FastAPI(title="SAP L1 Support Agent", version="1.0.0")

# In-memory store: thread_id → config dict
_threads: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AlertRequest(BaseModel):
    host: str
    sid: str
    nr: str = "00"
    alert: str


class AlertResponse(BaseModel):
    thread_id: str
    status: str


class ApproveRequest(BaseModel):
    decision: str  # "yes" | "no"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sap-l1-agent"}


@app.post("/alert", response_model=AlertResponse)
def create_alert(req: AlertRequest) -> AlertResponse:
    """Start a new incident analysis in a background thread."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    _threads[thread_id] = config

    initial_state = {
        "host": req.host,
        "sid": req.sid,
        "instance_nr": req.nr,
        "alert": req.alert,
        "thread_id": thread_id,
        "messages": [],
    }

    def _run() -> None:
        set_scenario(req.alert)
        compiled_graph.invoke(initial_state, config)

    Thread(target=_run, daemon=True).start()

    return AlertResponse(thread_id=thread_id, status="running")


@app.get("/status/{thread_id}")
def get_status(thread_id: str) -> dict[str, Any]:
    """Return the current graph state for a thread."""
    config = _threads.get(thread_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    state = compiled_graph.get_state(config)
    values = dict(state.values) if state.values else {}

    # Determine status
    if state.next:
        status = "waiting_for_approval"
    elif values.get("report"):
        status = "completed"
    else:
        status = "running"

    return {
        "thread_id": thread_id,
        "status": status,
        "next": list(state.next) if state.next else [],
        "rca_result": values.get("rca_result"),
        "report": values.get("report"),
    }


@app.post("/approve/{thread_id}")
def approve(thread_id: str, req: ApproveRequest) -> dict[str, str]:
    """Resume a paused graph with the operator's approval decision."""
    config = _threads.get(thread_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    state = compiled_graph.get_state(config)
    if not state.next:
        raise HTTPException(status_code=400, detail="Graph is not paused")

    decision = req.decision.lower().strip()
    if decision not in ("yes", "no"):
        raise HTTPException(status_code=400, detail="Decision must be 'yes' or 'no'")

    def _resume() -> None:
        compiled_graph.invoke(Command(resume=decision), config)

    Thread(target=_resume, daemon=True).start()

    return {"thread_id": thread_id, "status": "resumed", "decision": decision}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
