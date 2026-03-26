"""Seed Langfuse with the initial prompt versions.

Usage:
    python prompts_seed.py

This uploads the supervisor_routing and rca_synthesis prompts to Langfuse
so they can be edited in the UI. Run once, then manage prompts via the
Langfuse dashboard.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import settings
from langfuse_init import init_langfuse
from prompts import SUPERVISOR_ROUTING_FALLBACK, RCA_SYNTHESIS_FALLBACK

from langfuse import get_client


def seed() -> None:
    if not init_langfuse():
        print("Langfuse not configured. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY.")
        return

    client = get_client()

    prompts = {
        "supervisor_routing": SUPERVISOR_ROUTING_FALLBACK,
        "rca_synthesis": RCA_SYNTHESIS_FALLBACK,
    }

    for name, text in prompts.items():
        try:
            existing = client.get_prompt(name)
            print(f"  '{name}' already exists (version {existing.version}) — skipping")
        except Exception:
            client.create_prompt(
                name=name,
                prompt=text,
                labels=["production"],
                tags=["sap-l1-agent"],
                commit_message="Initial prompt version seeded from code",
            )
            print(f"  '{name}' created in Langfuse")

    print("\nDone. Manage prompts at:", settings.langfuse_host)


if __name__ == "__main__":
    seed()
