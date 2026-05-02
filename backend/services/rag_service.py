"""
rag_service.py
--------------
Retrieval-Augmented Generation service.

Flow:
  1. Build a semantic query from the current analysis
  2. Retrieve top-k similar past sessions from ChromaDB
  3. Summarise retrieved context into a compact paragraph
  4. Return augmented context string → injected into Gemini suggestion prompt
"""

from services.vector_store import retrieve_similar_sessions
from logger import setup_logger

logger = setup_logger(__name__)


class RAGService:

    def build_context(self, user_id: str, current_analysis: dict) -> str:
        """
        Retrieve relevant past sessions and format them as RAG context.
        Returns an empty string if no history exists.
        """
        query = self._build_query(current_analysis)
        sessions = retrieve_similar_sessions(user_id, query, n_results=3)

        if not sessions:
            logger.info(f"RAG: no history found for user {user_id}")
            return ""

        logger.info(f"RAG: retrieved {len(sessions)} past sessions for user {user_id}")
        return self._format_context(sessions)

    # ── internals ──────────────────────────────────────────────

    def _build_query(self, analysis: dict) -> str:
        """Build a semantic search query from the current analysis."""
        cats = [c["category"] for c in analysis.get("categories", [])[:3]]
        total = analysis.get("total_spent", 0)
        risk = analysis.get("risk_score", 0)
        return (
            f"expense analysis total spending ${total:.0f} "
            f"categories {' '.join(cats)} risk score {risk}"
        )

    def _format_context(self, sessions: list[dict]) -> str:
        """Format retrieved sessions into a compact context block for Gemini."""
        lines = ["=== USER'S PAST EXPENSE HISTORY (from memory) ==="]
        for i, s in enumerate(sessions, 1):
            meta = s["metadata"]
            sim = s["similarity"]
            lines.append(
                f"\n[Past Session {i}]  similarity={sim:.2f}"
                f"  date={meta.get('timestamp','?')[:10]}"
                f"  total=${meta.get('total_spent',0):.2f}"
                f"  limit=${meta.get('monthly_limit',0):.2f}"
                f"  risk={meta.get('risk_score',0)}/10"
                f"  top_category={meta.get('top_category','?')}"
            )
            # Include the full document text (truncated to keep prompt size reasonable)
            doc = s["document"]
            lines.append(doc[:800] + ("..." if len(doc) > 800 else ""))

        lines.append("=== END OF HISTORY ===")
        return "\n".join(lines)

    def summarise_trends(self, sessions: list[dict]) -> dict:
        """
        Aggregate metadata across all stored sessions for the history dashboard.
        """
        if not sessions:
            return {}

        totals = [s["metadata"].get("total_spent", 0) for s in sessions]
        risks = [s["metadata"].get("risk_score", 0) for s in sessions]
        limits = [s["metadata"].get("monthly_limit", 0) for s in sessions]

        from collections import Counter
        cat_counter = Counter(s["metadata"].get("top_category", "Other") for s in sessions)

        return {
            "session_count": len(sessions),
            "avg_spending": round(sum(totals) / len(totals), 2),
            "max_spending": round(max(totals), 2),
            "min_spending": round(min(totals), 2),
            "avg_risk": round(sum(risks) / len(risks), 2),
            "avg_limit": round(sum(limits) / len(limits), 2),
            "most_common_category": cat_counter.most_common(1)[0][0] if cat_counter else "N/A",
            "category_frequency": dict(cat_counter),
            "spending_trend": totals,  # chronological list for chart
        }