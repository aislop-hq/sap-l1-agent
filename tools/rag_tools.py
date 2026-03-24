"""Qdrant similarity search tool with DEMO_MODE support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from config import settings
from mock.mock_ssh import select_scenario

logger = logging.getLogger(__name__)


@dataclass
class RunbookMatch:
    title: str
    content: str
    sap_note: Optional[str]
    score: float


# ---------------------------------------------------------------------------
# Demo-mode hardcoded results (one per scenario)
# ---------------------------------------------------------------------------

_DEMO_RESULTS: dict[str, list[RunbookMatch]] = {
    "hung_wp": [
        RunbookMatch(
            title="Hung Work Process",
            content=(
                "Work process shows status STOPPED in sapcontrol ABAPGetWPTable. "
                "Check dev_w<N> trace for SIGSEGV or signal crash. "
                "Restart individual work process via sapcontrol RestartService. "
                "Apply SAP Note 1234567 if crash matches known SIGSEGV pattern."
            ),
            sap_note="1234567",
            score=0.95,
        ),
    ],
    "filesystem": [
        RunbookMatch(
            title="Filesystem Full",
            content=(
                "df -h shows /usr/sap/<SID>/work at >90%. "
                "Old trace files (dev_w*.old, dev_disp.old) consuming space. "
                "Remove old trace files and rotate current logs. "
                "Consider automated log rotation via cron."
            ),
            sap_note="2399996",
            score=0.93,
        ),
    ],
    "abap_dump": [
        RunbookMatch(
            title="ABAP Dump — TIME_OUT",
            content=(
                "ABAP runtime error TIME_OUT in dev_w* trace. "
                "Long-running report exceeds maximum runtime. "
                "Typically involves large SELECT without proper WHERE clause. "
                "Informational — escalate to ABAP development team."
            ),
            sap_note="1752526",
            score=0.91,
        ),
    ],
    "instance_down": [
        RunbookMatch(
            title="Instance Down",
            content=(
                "GetSystemInstanceList shows GRAY status. "
                "All processes stopped. Verify OS health before restart. "
                "Escalate — instance restart requires coordination. "
                "Notify application team and users before restart."
            ),
            sap_note="2318837",
            score=0.89,
        ),
    ],
}

# Map scenario dict id → demo key
_SCENARIO_KEYS = {
    "wp": "hung_wp",
    "work proc": "hung_wp",
    "filesystem": "filesystem",
    "disk": "filesystem",
    "dump": "abap_dump",
    "abap": "abap_dump",
    "instance": "instance_down",
    "down": "instance_down",
}


def _demo_lookup(alert: str) -> list[RunbookMatch]:
    """Return hardcoded RunbookMatch objects matching the alert scenario."""
    alert_lower = alert.lower()
    for keyword, key in _SCENARIO_KEYS.items():
        if keyword in alert_lower:
            return _DEMO_RESULTS[key]
    return _DEMO_RESULTS["hung_wp"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rag_lookup(query: str, alert: str = "", top_k: int = 3) -> list[RunbookMatch]:
    """Search SAP runbooks for content related to *query*.

    In DEMO_MODE, returns hardcoded results based on the *alert* string.
    In production, queries Qdrant with OpenAI embeddings.
    """
    if settings.demo_mode:
        results = _demo_lookup(alert or query)
        logger.info("[RCA] rag_lookup (mock): %d results for '%s'", len(results), query)
        return results

    try:
        from openai import OpenAI
        from qdrant_client import QdrantClient

        oai = OpenAI(api_key=settings.openai_api_key)
        qdrant = QdrantClient(url=settings.qdrant_url)

        embedding = (
            oai.embeddings.create(input=query, model="text-embedding-3-small")
            .data[0]
            .embedding
        )

        hits = qdrant.query_points(
            collection_name=settings.qdrant_collection,
            query=embedding,
            limit=top_k,
        ).points

        results: list[RunbookMatch] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                RunbookMatch(
                    title=payload.get("title", ""),
                    content=payload.get("content", ""),
                    sap_note=payload.get("sap_note"),
                    score=hit.score,
                )
            )

        logger.info("[RCA] rag_lookup: %d results for '%s'", len(results), query)
        return results

    except Exception as exc:
        logger.warning("[RCA] rag_lookup failed (Qdrant unreachable?): %s", exc)
        return []
