import google.generativeai as genai
from config import settings
from logger import setup_logger

logger = setup_logger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiService:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def classify_expense(self, description: str, amount: float) -> dict:
        prompt = f"""Classify this expense for a personal finance app.
Expense: "{description}" Amount: ${amount}

Return ONLY a JSON object (no markdown) with:
- category: one of [Food, Transport, Healthcare, Entertainment, Shopping, Utilities, Education, Housing, Other]
- is_essential: true or false
- reason: brief explanation

Example: {{"category": "Food", "is_essential": true, "reason": "Basic nutrition need"}}"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip().replace("```json", "").replace("```", "").strip()
            import json
            result = json.loads(text)
            logger.info(f"Gemini classified '{description}' as {result.get('category')}")
            return result
        except Exception as e:
            logger.error(f"Gemini classification error: {e}")
            return {"category": "Other", "is_essential": False, "reason": "Classification failed"}

    async def generate_suggestions(self, summary: dict) -> list:
        prompt = f"""You are a personal finance advisor. Analyze this expense summary and give 4 actionable tips.

Summary:
- Total spent: ${summary.get('total_spent', 0):.2f}
- Monthly limit: ${summary.get('monthly_limit', 0):.2f}
- Essential: ${summary.get('essential', 0):.2f}
- Non-essential: ${summary.get('non_essential', 0):.2f}
- Top categories: {summary.get('top_categories', [])}
- Risk score: {summary.get('risk_score', 0)}/10

Return ONLY a JSON array of 4 suggestion strings. No markdown, no preamble.
Example: ["Tip 1", "Tip 2", "Tip 3", "Tip 4"]"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip().replace("```json", "").replace("```", "").strip()
            import json
            suggestions = json.loads(text)
            logger.info("Gemini suggestions generated successfully")
            return suggestions
        except Exception as e:
            logger.error(f"Gemini suggestion error: {e}")
            return [
                "Review your non-essential spending",
                "Set category-wise budgets",
                "Track daily expenses",
                "Build an emergency fund"
            ]