"""Remediation agent node — write actions with human approval."""

from __future__ import annotations

import json
import logging

from langfuse import observe

from config import settings
from graph.state import AgentState
from tools.ssh_tools import SSHClient, set_scenario
from tools import sapcontrol_tools, log_tools

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
    host = state["host"]
    sid = state["sid"]
    nr = state["instance_nr"]
    alert = state["alert"]

    set_scenario(alert)

    with SSHClient(host=host) as ssh:
        if proposed_fix == "restart_workprocess":
            result = _do_restart_workprocess(ssh, nr)
        elif proposed_fix == "cleanup_filesystem":
            result = _do_cleanup_filesystem(ssh, sid)
        elif proposed_fix == "rotate_logs":
            result = _do_rotate_logs(ssh, sid)
        else:
            logger.info("[REMEDIATION] Unknown fix type: %s", proposed_fix)
            result = f"No handler for fix type: {proposed_fix}"
            return {"action_result": result}

        # Verify fix
        logger.info("[REMEDIATION] Verifying fix — re-running GetProcessList")
        verify = sapcontrol_tools.get_process_list(ssh, nr)
        verify_summary = json.dumps(verify, indent=2)
        logger.info("[REMEDIATION] Post-fix process list:\n%s", verify_summary)

    action_result = f"{result}\n\nVerification (GetProcessList):\n{verify_summary}"
    logger.info("[REMEDIATION] Remediation complete")
    return {"action_result": action_result}


def _do_restart_workprocess(ssh: SSHClient, nr: str) -> str:
    logger.info("[REMEDIATION] Restarting work process via RestartService")
    output = sapcontrol_tools.restart_service(ssh, nr)
    return f"RestartService executed.\n{output}"


def _do_cleanup_filesystem(ssh: SSHClient, sid: str) -> str:
    work_dir = f"/usr/sap/{sid}/work"
    logger.info("[REMEDIATION] Cleaning up old files in %s", work_dir)

    if settings.use_mock_ssh:
        return (
            f"Cleaned up old trace files in {work_dir}:\n"
            "  Removed dev_w0.old (2.1G)\n"
            "  Removed dev_w1.old (1.8G)\n"
            "  Removed dev_w2.old (1.5G)\n"
            "  Removed dev_disp.old (1.2G)\n"
            "  Removed dev_rd.old (800M)\n"
            "  Total freed: 7.4GB"
        )

    ssh.run_command(f"find {work_dir} -name '*.old' -mtime +30 -delete")
    return f"Removed *.old files older than 30 days from {work_dir}"


def _do_rotate_logs(ssh: SSHClient, sid: str) -> str:
    work_dir = f"/usr/sap/{sid}/work"
    logger.info("[REMEDIATION] Rotating logs in %s", work_dir)

    if settings.use_mock_ssh:
        return (
            f"Rotated logs in {work_dir}:\n"
            "  dev_w0 → dev_w0.old (120K)\n"
            "  dev_w1 → dev_w1.old (80K)\n"
            "  Logs rotated successfully"
        )

    ssh.run_command(
        f"cd {work_dir} && "
        "for f in dev_w[0-9]; do [ -f \"$f\" ] && mv \"$f\" \"$f.old\"; done"
    )
    return f"Rotated dev_w* logs in {work_dir}"
