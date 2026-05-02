from services.gemini_service import GeminiService
from logger import setup_logger

logger = setup_logger(__name__)


class SuggestionAgent:
    """Generates personalized financial suggestions using Gemini."""

    def __init__(self):
        self.gemini = GeminiService()

    async def run(self, data: dict) -> dict:
        logger.info("SuggestionAgent: generating suggestions")

        top_cats = [c["category"] for c in data.get("categories", [])[:3]]
        summary = {
            "total_spent": data["total_spent"],
            "monthly_limit": data["monthly_limit"],
            "essential": data["essential_total"],
            "non_essential": data["non_essential_total"],
            "top_categories": top_cats,
            "risk_score": data["risk_score"],
        }

        suggestions = await self.gemini.generate_suggestions(summary)
        data["suggestions"] = suggestions
        logger.info(f"SuggestionAgent: generated {len(suggestions)} suggestions")
        return data
