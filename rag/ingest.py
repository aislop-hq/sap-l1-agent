"""Load runbooks from rag/runbooks/ into Qdrant.

Usage:
    python rag/ingest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# Add project root to path so config is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings

RUNBOOKS_DIR = Path(__file__).resolve().parent / "runbooks"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a markdown file into YAML front-matter dict and body content."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return meta, body


def ingest() -> None:
    oai = OpenAI(api_key=settings.openai_api_key)
    qdrant = QdrantClient(url=settings.qdrant_url)

    # Ensure collection exists
    collections = [c.name for c in qdrant.get_collections().collections]
    if settings.qdrant_collection not in collections:
        qdrant.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"Created collection '{settings.qdrant_collection}'")

    md_files = sorted(RUNBOOKS_DIR.glob("*.md"))
    if not md_files:
        print("No runbook files found in", RUNBOOKS_DIR)
        return

    points: list[PointStruct] = []

    for idx, md_path in enumerate(md_files):
        print(f"[{idx + 1}/{len(md_files)}] Processing {md_path.name} …")
        raw = md_path.read_text()
        meta, body = parse_frontmatter(raw)

        # Build embedding input: title + keywords + body
        embed_text = f"{meta.get('title', '')} {' '.join(meta.get('keywords', []))} {body}"

        resp = oai.embeddings.create(input=embed_text, model=EMBEDDING_MODEL)
        vector = resp.data[0].embedding

        points.append(
            PointStruct(
                id=idx,
                vector=vector,
                payload={
                    "title": meta.get("title", md_path.stem),
                    "keywords": meta.get("keywords", []),
                    "sap_note": str(meta.get("sap_note", "")),
                    "risk": meta.get("risk", ""),
                    "content": body,
                    "source_file": md_path.name,
                },
            )
        )

    qdrant.upsert(collection_name=settings.qdrant_collection, points=points)
    print(f"Upserted {len(points)} runbooks into '{settings.qdrant_collection}'")


if __name__ == "__main__":
    ingest()
