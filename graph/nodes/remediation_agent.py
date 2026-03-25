"""Remediation agent node — executes fix commands from runbook-driven RCA."""

from __future__ import annotations

import logging

from langfuse import observe

from config import settings
from graph.state import AgentState
from tools.ssh_tools import SSHClient, set_scenario

logger = logging.getLogger(__name__)


@observe(name="remediation")
def remediation_agent_node(state: AgentState) -> dict:
    """Execute the approved remediation action and verify the fix."""
    decision = state.get("approval_decision")

    if decision != "yes":
        logger.info("[REMEDIATION] Action rejected by operator")
        return {"action_result": "Action rejected by operator"}

    rca = state.get("rca_result")
    if not rca:
        logger.warning("[REMEDIATION] No RCA result available")
        return {"action_result": "No RCA result — nothing to remediate"}

    proposed_fix = rca.get("proposed_fix", "")
    fix_command = rca.get("fix_command", "")
    verify_command = rca.get("verify_command", "")
    host = state["host"]
    sid = state["sid"]
    nr = state["instance_nr"]
    alert = state["alert"]

    if not fix_command or proposed_fix in ("none", "None", "escalate", ""):
        logger.info("[REMEDIATION] No fix command to execute (action=%s)", proposed_fix)
        return {"action_result": f"No fix command for action: {proposed_fix}"}

    # Substitute placeholders
    fix_command = _substitute(fix_command, sid=sid, nr=nr, host=host)
    verify_command = _substitute(verify_command, sid=sid, nr=nr, host=host) if verify_command else ""

    logger.info("[REMEDIATION] Executing: %s", fix_command)

    set_scenario(alert)

    with SSHClient(host=host) as ssh:
        # Execute fix
        fix_output = ssh.run_command(fix_command)
        result = f"Executed: {fix_command}\n{fix_output}"

        # Verify if a verify command is defined
        if verify_command:
            logger.info("[REMEDIATION] Verifying: %s", verify_command)
            verify_output = ssh.run_command(verify_command)
            result += f"\n\nVerification ({verify_command}):\n{verify_output}"

    logger.info("[REMEDIATION] Remediation complete")
    return {"action_result": result}


def _substitute(cmd: str, sid: str, nr: str, host: str) -> str:
    """Replace {SID}, {NR}, {HOST} placeholders in a command template."""
    return cmd.replace("{SID}", sid).replace("{NR}", nr).replace("{HOST}", host)
