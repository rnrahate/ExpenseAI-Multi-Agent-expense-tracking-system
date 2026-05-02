from backend.services.gemini_service import GeminiService
from backend.logger import setup_logger

logger = setup_logger(__name__)

ESSENTIAL_CATEGORIES = {"Food", "Healthcare", "Utilities", "Education", "Housing", "Transport"}
RULE_BASED_KEYWORDS = {
    "Food": ["grocery", "groceries", "restaurant", "food", "meal", "lunch", "dinner", "breakfast", "coffee", "pizza", "bread", "milk"],
    "Transport": ["uber", "ola", "taxi", "bus", "metro", "petrol", "fuel", "parking", "train", "flight"],
    "Healthcare": ["medicine", "doctor", "hospital", "pharmacy", "clinic", "health", "dental", "medical"],
    "Entertainment": ["netflix", "spotify", "movie", "cinema", "game", "concert", "party", "bar", "club"],
    "Shopping": ["amazon", "flipkart", "clothes", "shoes", "fashion", "mall", "shopping"],
    "Utilities": ["electricity", "water", "gas", "internet", "wifi", "broadband", "phone bill", "recharge"],
    "Education": ["course", "book", "tuition", "school", "college", "udemy", "coursera"],
    "Housing": ["rent", "mortgage", "maintenance", "repair", "furniture"],
}


class ClassificationAgent:
    """Classifies each expense using rules first, Gemini as fallback."""

    def __init__(self):
        self.gemini = GeminiService()

    def _rule_based_classify(self, description: str) -> dict | None:
        desc_lower = description.lower()
        for category, keywords in RULE_BASED_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                return {
                    "category": category,
                    "is_essential": category in ESSENTIAL_CATEGORIES,
                    "reason": "Rule-based match"
                }
        return None

    async def run(self, data: dict) -> dict:
        expenses = data["expenses"]
        logger.info(f"ClassificationAgent: classifying {len(expenses)} expenses")

        for exp in expenses:
            rule_result = self._rule_based_classify(exp["description"])
            if rule_result:
                exp.update(rule_result)
                exp["classified"] = True
                exp["classification_method"] = "rule"
            else:
                gemini_result = await self.gemini.classify_expense(exp["description"], exp["amount"])
                exp["category"] = gemini_result.get("category", "Other")
                exp["is_essential"] = gemini_result.get("is_essential", False)
                exp["reason"] = gemini_result.get("reason", "")
                exp["classified"] = True
                exp["classification_method"] = "gemini"

        logger.info("ClassificationAgent: classification complete")
        data["expenses"] = expenses
        return data
