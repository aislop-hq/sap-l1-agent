"""dev_w* log reading and filesystem inspection tools."""

from __future__ import annotations

import logging

from tools.ssh_tools import SSHClient

logger = logging.getLogger(__name__)


def read_dev_log(ssh: SSHClient, sid: str, instance_nr: str, wp_nr: int) -> str:
    """Read ``/usr/sap/{SID}/work/dev_w{wp_nr}`` from the remote host."""
    path = f"/usr/sap/{sid}/work/dev_w{wp_nr}"
    logger.info("[RCA] read_dev_log: %s", path)
    return ssh.read_file(path)


def get_filesystem_usage(ssh: SSHClient) -> str:
    """Run ``df -h`` and return the output."""
    logger.info("[RCA] get_filesystem_usage")
    return ssh.run_command("df -h")


def find_old_files(ssh: SSHClient, directory: str, days: int = 30) -> str:
    """List files in *directory* older than *days* days via ``ls -lh``."""
    logger.info("[RCA] find_old_files: %s (>%d days)", directory, days)
    return ssh.run_command(f"ls -lh {directory}")
