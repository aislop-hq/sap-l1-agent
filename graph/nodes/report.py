"""Report node — generates structured IncidentReport and prints it."""

from __future__ import annotations

import logging
import uuid

from langfuse import observe, get_client
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from graph.state import AgentState, IncidentReport

logger = logging.getLogger(__name__)
console = Console()


@observe(name="report_generation")
def report_node(state: AgentState) -> dict:
    """Assemble and display the final IncidentReport."""
    rca = state.get("rca_result")
    decision = state.get("approval_decision")
    action_result = state.get("action_result")

    # Determine resolution status
    escalate = False
    resolved = False

    if rca:
        risk = rca.get("risk_level", "LOW")
        proposed_fix = rca.get("proposed_fix", "")

        if risk == "HIGH" or proposed_fix == "escalate":
            escalate = True
        elif proposed_fix in ("None", "n/a", "", None):
            # Informational only
            resolved = True
        elif decision == "yes" and action_result and "rejected" not in action_result.lower():
            resolved = True

    action_taken = None
    if decision == "yes":
        action_taken = rca.get("proposed_fix", "unknown") if rca else "unknown"
    elif decision == "no":
        action_taken = "rejected by operator"

    report = IncidentReport(
        incident_id=state.get("thread_id", str(uuid.uuid4())),
        host=state.get("host", "unknown"),
        alert=state.get("alert", "unknown"),
        rca=rca,
        action_taken=action_taken,
        action_result=action_result,
        resolved=resolved,
        escalate=escalate,
    )

    # Log Langfuse scores
    try:
        client = get_client()
        thread_id = state.get("thread_id", "")
        if decision is not None:
            client.score(trace_id=thread_id, name="operator_approval", value=1 if decision == "yes" else 0)
        client.score(trace_id=thread_id, name="resolved", value=1 if resolved else 0)
        client.score(trace_id=thread_id, name="escalated", value=1 if escalate else 0)
    except Exception:
        pass  # Langfuse may not be configured

    # Print report
    _print_report(report)

    logger.info("[REPORT] Incident %s — resolved=%s, escalate=%s",
                report["incident_id"], resolved, escalate)

    return {"report": report}


def _print_report(report: IncidentReport) -> None:
    """Render the IncidentReport as a Rich panel."""
    rca = report.get("rca")

    # Header
    if report["escalate"]:
        title = "[bold red]ESCALATION REQUIRED[/bold red]"
    elif report["resolved"]:
        title = "[bold green]RESOLVED[/bold green]"
    else:
        title = "[bold yellow]INFORMATIONAL[/bold yellow]"

    # Build report table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", width=18)
    table.add_column("Value")

    table.add_row("Incident ID", report["incident_id"])
    table.add_row("Host", report["host"])
    table.add_row("Alert", report["alert"])

    if rca:
        table.add_row("Root Cause", rca.get("root_cause", "N/A"))
        table.add_row("Confidence", rca.get("confidence", "N/A"))
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

    if report["action_taken"]:
        table.add_row("Action Taken", report["action_taken"])
    if report["action_result"]:
        # Truncate long action results for display
        result_text = report["action_result"]
        if len(result_text) > 200:
            result_text = result_text[:200] + "..."
        table.add_row("Action Result", result_text)

    table.add_row("Resolved", str(report["resolved"]))
    table.add_row("Escalate", str(report["escalate"]))

    console.print()
    console.print(Panel(table, title=f"Incident Report — {title}", border_style="blue"))
    console.print()
