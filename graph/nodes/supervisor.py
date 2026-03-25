"""Supervisor node — routes the graph to the next agent."""

from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI
from langfuse import observe

from config import settings
from graph.state import AgentState

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model=settings.openai_model, temperature=0, base_url=settings.openai_base_url, api_key=settings.openai_api_key)

_ROUTING_PROMPT = """\
You are the Supervisor of an SAP Basis L1 support agent system.

Current state:
- Alert: {alert}
- RCA completed: {rca_done}
- RCA result: {rca_summary}

Decide the next step. Respond with ONLY a JSON object (no markdown):
{{"next": "<target>", "reason": "<short reason>"}}

Possible targets:
- "rca_agent"        → run root-cause analysis (use when RCA has not been done yet)
- "human_approval"   → ask operator to approve a fix (use when RCA found a fixable issue with proposed_fix)
- "report"           → go straight to report (use when RCA is informational-only OR the issue requires escalation, i.e. risk_level is HIGH)
"""


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
        if not proposed_fix or proposed_fix.lower() in ("none", "n/a", ""):
            logger.info("[SUPERVISOR] No fix proposed → routing to report")
            return {"next": "report"}
        logger.info("[SUPERVISOR] Fix proposed → routing to human_approval")
        return {"next": "human_approval"}

    # Production: use LLM to decide
    prompt = _ROUTING_PROMPT.format(
        alert=state["alert"],
        rca_done=rca_done,
        rca_summary=rca_summary,
    )

    response = _llm.invoke(prompt)
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
