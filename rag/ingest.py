"""Load runbooks from rag/runbooks/ into Qdrant.

Supports chunking — large documents are split into overlapping sections
so that each chunk fits well within the embedding model's sweet spot.

Usage:
    python rag/ingest.py
    python rag/ingest.py --collection my_collection
    python rag/ingest.py --dry-run   # parse and chunk without embedding
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml

# Add project root to path so config is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings

RUNBOOKS_DIR = Path(__file__).resolve().parent / "runbooks"
EMBEDDING_MODEL = settings.openai_embedding_model
EMBEDDING_DIM = 1536
CHUNK_SIZE = 1500      # characters per chunk (≈375 tokens)
CHUNK_OVERLAP = 200    # overlap between consecutive chunks


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


def chunk_by_sections(body: str, max_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split markdown body into chunks, preferring section boundaries.

    Tries to split on ## headings first.  If a section is still too large,
    falls back to paragraph-level splitting with overlap.
    """
    # Split on ## headings, keeping the heading with its section
    sections = re.split(r"(?=^## )", body, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks: list[str] = []
    for section in sections:
        if len(section) <= max_size:
            chunks.append(section)
        else:
            # Sub-split long sections by paragraphs
            paragraphs = section.split("\n\n")
            current = ""
            for para in paragraphs:
                if len(current) + len(para) + 2 > max_size and current:
                    chunks.append(current.strip())
                    # Keep overlap from end of previous chunk
                    current = current[-overlap:] + "\n\n" + para if overlap else para
                else:
                    current = current + "\n\n" + para if current else para
            if current.strip():
                chunks.append(current.strip())

    return chunks if chunks else [body]


def ingest(collection: str | None = None, dry_run: bool = False) -> None:
    collection = collection or settings.qdrant_collection

    md_files = sorted(RUNBOOKS_DIR.glob("*.md"))
    if not md_files:
        print("No runbook files found in", RUNBOOKS_DIR)
        return

    # Parse and chunk all documents first
    all_chunks: list[dict] = []
    for md_path in md_files:
        raw = md_path.read_text()
        meta, body = parse_frontmatter(raw)
        title = meta.get("title", md_path.stem)
        keywords = meta.get("keywords", [])

        chunks = chunk_by_sections(body)
        print(f"  {md_path.name}: {len(chunks)} chunk(s)")

        for i, chunk in enumerate(chunks):
            # Deterministic ID from file + chunk index
            chunk_id = hashlib.md5(f"{md_path.name}:{i}".encode()).hexdigest()
            chunk_id_int = int(chunk_id[:16], 16)  # Qdrant needs int or uuid

            all_chunks.append({
                "id": chunk_id_int,
                "text": f"{title}\n{' '.join(str(k) for k in keywords)}\n\n{chunk}",
                "payload": {
                    "title": title,
                    "keywords": keywords,
                    "sap_note": str(meta.get("sap_note", "")),
                    "risk": meta.get("risk", ""),
                    "content": chunk,
                    "source_file": md_path.name,
                    "chunk_index": i,
                },
            })

    print(f"\nTotal: {len(all_chunks)} chunks from {len(md_files)} runbooks")

    if dry_run:
        print("\n[dry-run] Skipping embedding and upsert.")
        for c in all_chunks:
            preview = c["payload"]["content"][:80].replace("\n", " ")
            print(f"  - {c['payload']['source_file']}#{c['payload']['chunk_index']}: {preview}…")
        return

    # Embed and upsert
    from openai import OpenAI
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    oai = OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key)
    qdrant = QdrantClient(url=settings.qdrant_url)

    # Ensure collection exists
    collections = [c.name for c in qdrant.get_collections().collections]
    if collection not in collections:
        qdrant.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"Created collection '{collection}'")
    else:
        print(f"Using existing collection '{collection}'")

    # Batch embed (OpenAI supports up to 2048 inputs per call)
    texts = [c["text"] for c in all_chunks]
    print(f"Embedding {len(texts)} chunks with {EMBEDDING_MODEL}…")

    batch_size = 100
    all_vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        resp = oai.embeddings.create(input=batch, model=EMBEDDING_MODEL)
        all_vectors.extend(e.embedding for e in resp.data)
        print(f"  Embedded {min(start + batch_size, len(texts))}/{len(texts)}")

    # Build points
    points = [
        PointStruct(
            id=c["id"],
            vector=vec,
            payload=c["payload"],
        )
        for c, vec in zip(all_chunks, all_vectors)
    ]

    qdrant.upsert(collection_name=collection, points=points)
    print(f"\nUpserted {len(points)} chunks into '{collection}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest SAP runbooks into Qdrant")
    parser.add_argument("--collection", help="Qdrant collection name")
    parser.add_argument("--dry-run", action="store_true", help="Parse and chunk without embedding")
    args = parser.parse_args()
    ingest(collection=args.collection, dry_run=args.dry_run)
