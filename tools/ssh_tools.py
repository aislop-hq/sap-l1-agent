"""Paramiko SSH wrapper — all SSH commands go through this module."""

from __future__ import annotations

import logging
from typing import Optional

import paramiko

from config import settings
from mock.mock_ssh import mock_command

logger = logging.getLogger(__name__)

# Module-level alert string used by DEMO_MODE to select the right scenario.
_current_alert: str = ""


def set_scenario(alert: str) -> None:
    """Set the alert string so mock lookups pick the correct scenario."""
    global _current_alert
    _current_alert = alert
    logger.info("[SSH] Scenario set to: %s", alert)


class SSHClient:
    """Thin wrapper around paramiko that respects DEMO_MODE."""

    def __init__(
        self,
        host: str,
        user: Optional[str] = None,
        key_path: Optional[str] = None,
    ) -> None:
        self.host = host
        self.user = user or settings.ssh_default_user
        self.key_path = key_path or str(settings.ssh_key_resolved)
        self._client: Optional[paramiko.SSHClient] = None

    # -- connection management ------------------------------------------------

    def _connect(self) -> paramiko.SSHClient:
        if self._client is not None:
            return self._client
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.host,
            username=self.user,
            key_filename=self.key_path,
        )
        self._client = client
        logger.info("[SSH] Connected to %s@%s", self.user, self.host)
        return client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("[SSH] Disconnected from %s", self.host)

    # -- public API -----------------------------------------------------------

    def run_command(self, cmd: str) -> str:
        """Execute *cmd* on the remote host and return stdout as a string.

        In DEMO_MODE the command is resolved against the mock scenario
        selected by :func:`set_scenario`.
        """
        logger.info("[RCA] ssh_run: %s", cmd)

        if settings.use_mock_ssh:
            output = mock_command(_current_alert, cmd)
            logger.info("[RCA] (mock) returned %d chars", len(output))
            return output

        client = self._connect()
        _, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if err:
            logger.warning("[SSH] stderr from %s: %s", cmd, err.strip())
        return out

    def read_file(self, path: str) -> str:
        """Read the contents of a remote file.

        In DEMO_MODE, the file basename is matched against the mock
        scenario so that e.g. ``/usr/sap/DEV/work/dev_w2`` matches the
        ``dev_w2`` key.
        """
        logger.info("[RCA] read_file: %s", path)

        if settings.use_mock_ssh:
            output = mock_command(_current_alert, path)
            logger.info("[RCA] (mock) returned %d chars", len(output))
            return output

        return self.run_command(f"cat {path}")

    # -- context manager ------------------------------------------------------

    def __enter__(self) -> "SSHClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
