"""Langfuse initialization — call once at startup to configure tracing.

If credentials are not set, tracing is silently disabled.

IMPORTANT: This module also sets LANGFUSE_ENABLED=false at import time
if no credentials are configured, so that the @observe decorators
(evaluated at module import) don't emit auth warnings.
"""

from __future__ import annotations

import logging
import os

from config import settings

logger = logging.getLogger(__name__)

# Set immediately at import so @observe decorators don't warn
if not settings.langfuse_public_key or not settings.langfuse_secret_key:
    os.environ.setdefault("LANGFUSE_ENABLED", "false")
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-stub")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-stub")
    os.environ.setdefault("LANGFUSE_HOST", "http://localhost:0")


def init_langfuse() -> bool:
    """Configure Langfuse env vars so the `@observe` decorator picks them up.

    Returns True if Langfuse is configured, False otherwise.
    """
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("[LANGFUSE] No credentials set — tracing disabled")
        return False

    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    os.environ["LANGFUSE_HOST"] = settings.langfuse_host
    os.environ["LANGFUSE_ENABLED"] = "true"

    logger.info("[LANGFUSE] Tracing enabled → %s", settings.langfuse_host)
    return True
