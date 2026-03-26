"""Supervisor node — routes the graph to the next agent."""

from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI
from langfuse import observe
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler

from config import settings
from graph.state import AgentState
from prompts import get_prompt_text

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model=settings.openai_model, temperature=0, base_url=settings.openai_base_url, api_key=settings.openai_api_key)
_langfuse_handler = LangfuseCallbackHandler()


@observe(name="supervisor_route")
def supervisor_node(state: AgentState) -> dict:
    """Route the graph to the next node based on current state."""
    rca = state.get("rca_result")
    rca_done = rca is not None

    if not rca_done:
        # First pass — always go to RCA
        logger.info("[SUPERVISOR] No RCA yet, routing to rca_agent")
        return {"next": "rca_agent"}

    rca_summary = json.dumps(rca, indent=2) if rca else "N/A"

    if settings.demo_mode:
        # Deterministic routing in demo mode to avoid LLM dependency
        risk = rca.get("risk_level", "LOW") if rca else "LOW"
        proposed_fix = rca.get("proposed_fix", "") if rca else ""

        if risk == "HIGH":
            logger.info("[SUPERVISOR] Risk HIGH → routing to report (escalation)")
            return {"next": "report"}
        if not proposed_fix or proposed_fix.lower() in ("none", "n/a", "", "escalate"):
            logger.info("[SUPERVISOR] No fix / escalation → routing to report")
            return {"next": "report"}
        logger.info("[SUPERVISOR] Fix proposed → routing to human_approval")
        return {"next": "human_approval"}

    # Production: use LLM to decide
    prompt = get_prompt_text("supervisor_routing", {
        "alert": state["alert"],
        "rca_done": str(rca_done),
        "rca_summary": rca_summary,
    })

    response = _llm.invoke(prompt, config={"callbacks": [_langfuse_handler]})
    try:
        decision = json.loads(response.content)
        next_node = decision["next"]
        reason = decision.get("reason", "")
    except (json.JSONDecodeError, KeyError):
        logger.warning("[SUPERVISOR] Failed to parse LLM response, defaulting to report")
        next_node = "report"
        reason = "parse failure"

    logger.info("[SUPERVISOR] Routing to %s (%s)", next_node, reason)
    return {"next": next_node}
