"""LangGraph graph definition — the core agent workflow."""

from __future__ import annotations

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from graph.state import AgentState
from graph.nodes.supervisor import supervisor_node
from graph.nodes.rca_agent import rca_agent_node
from graph.nodes.remediation_agent import remediation_agent_node
from graph.nodes.report import report_node

logger = logging.getLogger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# Human approval node — uses interrupt() to pause the graph
# ---------------------------------------------------------------------------

def human_approval_node(state: AgentState) -> dict:
    """Surface RCAResult to the operator and pause for approval."""
    rca = state.get("rca_result")

    if rca:
        # Print a formatted approval box
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="bold cyan", width=16)
        table.add_column("Value")

        table.add_row("Root Cause", rca.get("root_cause", "N/A"))
        table.add_row("Confidence", rca.get("confidence", "N/A"))
        table.add_row("Proposed Fix", rca.get("proposed_fix", "N/A"))
        if rca.get("fix_command"):
            table.add_row("Fix Command", rca.get("fix_command", ""))
        table.add_row("Risk Level", rca.get("risk_level", "N/A"))
        table.add_row("SAP Note", rca.get("sap_note_ref") or "N/A")

        symptoms = rca.get("symptoms", [])
        if symptoms:
            table.add_row("Symptoms", symptoms[0])
            for s in symptoms[1:]:
                table.add_row("", s)

        evidence = rca.get("evidence", [])
        if evidence:
            table.add_row("Evidence", evidence[0])
            for e in evidence[1:]:
                table.add_row("", e)

        console.print()
        console.print(Panel(
            table,
            title="[bold yellow]Approval Required[/bold yellow]",
            border_style="yellow",
        ))

    # Pause the graph and wait for human input
    decision = interrupt({
        "rca": rca,
        "proposed_fix": rca.get("proposed_fix", "") if rca else "",
        "risk_level": rca.get("risk_level", "") if rca else "",
        "message": "Do you approve this remediation action?",
    })

    logger.info("[SUPERVISOR] Human approval decision: %s", decision)
    return {"approval_decision": decision}


# ---------------------------------------------------------------------------
# Routing function — reads state.next to pick the next node
# ---------------------------------------------------------------------------

def route_supervisor(state: AgentState) -> str:
    """Return the next node name based on the supervisor's decision."""
    target = state.get("next", "report")
    if target in ("rca_agent", "human_approval", "remediation_agent", "report"):
        return target
    return "report"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rca_agent", rca_agent_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("remediation_agent", remediation_agent_node)
    graph.add_node("report", report_node)

    # Entry point
    graph.set_entry_point("supervisor")

    # Supervisor routes conditionally
    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "rca_agent": "rca_agent",
            "human_approval": "human_approval",
            "remediation_agent": "remediation_agent",
            "report": "report",
        },
    )

    # After RCA, go back to supervisor for routing decision
    graph.add_edge("rca_agent", "supervisor")

    # After approval, go to remediation
    graph.add_edge("human_approval", "remediation_agent")

    # After remediation, go to report
    graph.add_edge("remediation_agent", "report")

    # Report is the terminal node
    graph.add_edge("report", END)

    return graph


# ---------------------------------------------------------------------------
# Compiled graph with MemorySaver checkpointer
# ---------------------------------------------------------------------------

memory = MemorySaver()
compiled_graph = build_graph().compile(checkpointer=memory)
