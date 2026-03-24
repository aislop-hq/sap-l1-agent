"""sapcontrol command wrappers.

Every function takes an SSHClient, SID, and instance number, builds the
appropriate ``sapcontrol`` CLI call, and returns either raw output or a
parsed structure.
"""

from __future__ import annotations

import logging
from typing import Any

from tools.ssh_tools import SSHClient

logger = logging.getLogger(__name__)


def _sapcontrol_cmd(nr: str, function: str) -> str:
    return f"sapcontrol -nr {nr} -function {function}"


# ---------------------------------------------------------------------------
# Read-only queries
# ---------------------------------------------------------------------------

def get_process_list(ssh: SSHClient, nr: str) -> list[dict[str, str]]:
    """Return parsed output of ``GetProcessList``."""
    raw = ssh.run_command(_sapcontrol_cmd(nr, "GetProcessList"))
    return _parse_csv(raw)


def get_wp_table(ssh: SSHClient, nr: str) -> list[dict[str, str]]:
    """Return parsed output of ``ABAPGetWPTable``."""
    raw = ssh.run_command(_sapcontrol_cmd(nr, "ABAPGetWPTable"))
    return _parse_csv(raw)


def get_instance_list(ssh: SSHClient, nr: str) -> list[dict[str, str]]:
    """Return parsed output of ``GetSystemInstanceList``."""
    raw = ssh.run_command(_sapcontrol_cmd(nr, "GetSystemInstanceList"))
    return _parse_csv(raw)


def get_alert_tree(ssh: SSHClient, nr: str) -> str:
    """Return raw output of ``GetAlertTree``."""
    return ssh.run_command(_sapcontrol_cmd(nr, "GetAlertTree"))


# ---------------------------------------------------------------------------
# Write actions
# ---------------------------------------------------------------------------

def restart_service(ssh: SSHClient, nr: str) -> str:
    """Restart the SAP instance via ``RestartService``."""
    logger.info("[REMEDIATION] RestartService on instance %s", nr)
    return ssh.run_command(_sapcontrol_cmd(nr, "RestartService"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_csv(raw: str) -> list[dict[str, str]]:
    """Parse sapcontrol comma-separated output into a list of dicts.

    The first line is treated as the header row.  Extra whitespace in
    both keys and values is stripped.
    """
    lines = [l for l in raw.strip().splitlines() if l.strip()]
    if not lines:
        return []

    headers = [h.strip() for h in lines[0].split(",")]
    rows: list[dict[str, str]] = []
    for line in lines[1:]:
        values = [v.strip() for v in line.split(",")]
        row = dict(zip(headers, values))
        rows.append(row)
    return rows
