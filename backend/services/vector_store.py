"""
vector_store.py
---------------
Persistent ChromaDB vector store.
Each user gets their own collection (keyed by user_id).
Stores serialized expense analysis snapshots as documents,
with metadata for filtering. Embeddings use sentence-transformers
(all-MiniLM-L6-v2 — fast, lightweight, runs locally).
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from backend.logger import setup_logger

logger = setup_logger(__name__)

# ── Persistent ChromaDB client (data saved to ./chroma_db/) ──
_chroma_client: Optional[chromadb.PersistentClient] = None
_embedder: Optional[SentenceTransformer] = None
CHROMA_PATH = "./chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"


def _get_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB client initialised at {CHROMA_PATH}")
    return _chroma_client


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        logger.info(f"Loading embedding model: {EMBED_MODEL}")
        _embedder = SentenceTransformer(EMBED_MODEL)
        logger.info("Embedding model loaded")
    return _embedder


def _user_collection_name(user_id: str) -> str:
    """Each user has an isolated ChromaDB collection."""
    safe = hashlib.md5(user_id.encode()).hexdigest()[:16]
    return f"user_{safe}"


# ─────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────

def store_analysis(user_id: str, analysis: dict) -> str:
    """
    Persist one expense-analysis snapshot to the user's vector collection.
    Returns the document id.
    """
    client = _get_client()
    embedder = _get_embedder()
    collection = client.get_or_create_collection(
        name=_user_collection_name(user_id),
        metadata={"hnsw:space": "cosine"},
    )

    # Build a rich text document that captures the semantics of the session
    doc_text = _build_document_text(analysis)
    embedding = embedder.encode(doc_text).tolist()

    ts = datetime.now(timezone.utc).isoformat()
    doc_id = f"{user_id}_{hashlib.md5(ts.encode()).hexdigest()[:8]}"

    # Store lightweight metadata for fast filtering/display
    metadata = {
        "user_id": user_id,
        "timestamp": ts,
        "total_spent": analysis.get("total_spent", 0),
        "monthly_limit": analysis.get("monthly_limit", 0),
        "risk_score": analysis.get("risk_score", 0),
        "top_category": (analysis.get("categories") or [{}])[0].get("category", "Unknown"),
        "alert_count": len(analysis.get("alerts", [])),
        "essential_total": analysis.get("essential_total", 0),
        "non_essential_total": analysis.get("non_essential_total", 0),
    }

    collection.upsert(
        ids=[doc_id],
        documents=[doc_text],
        embeddings=[embedding],
        metadatas=[metadata],
    )
    logger.info(f"Stored analysis {doc_id} for user {user_id}")
    return doc_id


def retrieve_similar_sessions(
    user_id: str,
    query: str,
    n_results: int = 3,
) -> list[dict]:
    """
    Retrieve the top-k most semantically similar past sessions for a user.
    Returns list of dicts with 'document' and 'metadata'.
    """
    client = _get_client()
    embedder = _get_embedder()

    col_name = _user_collection_name(user_id)
    try:
        collection = client.get_collection(col_name)
    except Exception:
        logger.info(f"No history collection for user {user_id}")
        return []

    count = collection.count()
    if count == 0:
        return []

    query_embedding = embedder.encode(query).tolist()
    k = min(n_results, count)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    sessions = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        sessions.append({
            "document": doc,
            "metadata": meta,
            "similarity": round(1 - dist, 4),   # cosine distance → similarity
        })

    logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
    return sessions


def get_all_sessions(user_id: str) -> list[dict]:
    """Return all stored sessions for a user, newest first."""
    client = _get_client()
    col_name = _user_collection_name(user_id)
    try:
        collection = client.get_collection(col_name)
    except Exception:
        return []

    if collection.count() == 0:
        return []

    results = collection.get(include=["documents", "metadatas"])
    sessions = [
        {"document": d, "metadata": m}
        for d, m in zip(results["documents"], results["metadatas"])
    ]
    # Sort by timestamp descending
    sessions.sort(key=lambda x: x["metadata"].get("timestamp", ""), reverse=True)
    return sessions


def delete_user_history(user_id: str) -> bool:
    """Wipe all stored sessions for a user."""
    client = _get_client()
    col_name = _user_collection_name(user_id)
    try:
        client.delete_collection(col_name)
        logger.info(f"Deleted history for user {user_id}")
        return True
    except Exception as e:
        logger.warning(f"Could not delete history for {user_id}: {e}")
        return False


# ─────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────

def _build_document_text(analysis: dict) -> str:
    """
    Convert an analysis snapshot into a rich natural-language document
    that the embedding model can meaningfully encode.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = analysis.get("total_spent", 0)
    limit = analysis.get("monthly_limit", 0)
    essential = analysis.get("essential_total", 0)
    non_ess = analysis.get("non_essential_total", 0)
    risk = analysis.get("risk_score", 0)
    cats = analysis.get("categories", [])
    alerts = analysis.get("alerts", [])
    suggestions = analysis.get("suggestions", [])
    patterns = analysis.get("patterns", [])
    expenses = analysis.get("classified_expenses", [])

    cat_lines = "\n".join(
        f"  - {c['category']}: ${c['total']:.2f} ({c['count']} transactions)"
        for c in cats
    )
    alert_lines = "\n".join(f"  - [{a['severity'].upper()}] {a['message']}" for a in alerts)
    suggestion_lines = "\n".join(f"  - {s}" for s in suggestions)
    pattern_lines = "\n".join(f"  - {p}" for p in patterns)
    expense_lines = "\n".join(
        f"  - {e['description']}: ${e['amount']:.2f} [{e.get('category','Other')}] "
        f"{'essential' if e.get('is_essential') else 'non-essential'}"
        for e in expenses[:20]  # cap at 20 to keep doc size sane
    )

    return f"""Expense Analysis Session — {ts}

SUMMARY
Total spent: ${total:.2f} | Monthly limit: ${limit:.2f} | Remaining: ${limit-total:.2f}
Essential spending: ${essential:.2f} | Non-essential: ${non_ess:.2f}
Financial risk score: {risk}/10

CATEGORY BREAKDOWN
{cat_lines}

SPENDING PATTERNS
{pattern_lines}

ALERTS ({len(alerts)})
{alert_lines}

INDIVIDUAL EXPENSES
{expense_lines}

AI SUGGESTIONS
{suggestion_lines}
"""
