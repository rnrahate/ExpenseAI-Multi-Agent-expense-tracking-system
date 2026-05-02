import asyncio
import json
import subprocess
import sys

from config import settings
from logger import setup_logger

logger = setup_logger(__name__)
GEMINI_TIMEOUT_SECONDS = 15
GEMINI_MODEL_NAME = "gemini-1.5-flash"


class GeminiService:
    def _generate_json_sync(self, prompt: str) -> str:
        worker_code = """
import sys
import google.generativeai as genai

prompt = sys.argv[1]
api_key = sys.argv[2]
timeout = int(sys.argv[3])

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content(prompt, request_options={'timeout': timeout})
text = response.text.strip().replace('```json', '').replace('```', '').strip()
print(text)
"""
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                worker_code,
                prompt,
                settings.GEMINI_API_KEY,
                str(GEMINI_TIMEOUT_SECONDS),
            ],
            capture_output=True,
            text=True,
            timeout=GEMINI_TIMEOUT_SECONDS + 2,
            check=False,
        )

        if completed.returncode != 0:
            error_output = completed.stderr.strip() or completed.stdout.strip() or "Gemini request failed"
            raise RuntimeError(error_output)

        text = completed.stdout.strip()
        if not text:
            raise RuntimeError("Gemini returned no result")
        return text

    async def _generate_json(self, prompt: str) -> str:
        return await asyncio.to_thread(self._generate_json_sync, prompt)

    async def classify_expense(self, description: str, amount: float) -> dict:
        prompt = f"""Classify this expense for a personal finance app.
Expense: "{description}" Amount: ${amount}

Return ONLY a JSON object (no markdown) with:
- category: one of [Food, Transport, Healthcare, Entertainment, Shopping, Utilities, Education, Housing, Other]
- is_essential: true or false
- reason: brief explanation

Example: {{"category": "Food", "is_essential": true, "reason": "Basic nutrition need"}}"""
        try:
            text = await self._generate_json(prompt)
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
            text = await self._generate_json(prompt)
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
