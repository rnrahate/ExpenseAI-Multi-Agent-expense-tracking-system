from collections import defaultdict
import json

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)

from backend.agents.output_models import PatternResponseModel
from backend.agents.state import ExpenseGraphState
from backend.logger import setup_logger
from backend.services.gemini_service import GeminiService

logger = setup_logger(__name__)


class PatternAgent:
    """Computes exact spending metrics and uses a prompt-guided agent for pattern narratives."""

    def __init__(self):
        self.gemini = GeminiService()
        self.parser = PydanticOutputParser(pydantic_object=PatternResponseModel)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """You are PatternAgent inside a LangGraph personal finance workflow.

Actions to perform:
1. Review the spending summary and category breakdown.
2. Identify 2 to 5 concise, high-signal spending patterns.
3. Focus on budget pressure, dominant categories, diversification, and unusual concentration.
4. Do not repeat the raw numbers unnecessarily.
5. Return only structured output that follows the schema instructions.

{format_instructions}"""
                    )
                ),
                HumanMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """Expense summary:
{summary_json}"""
                    )
                ),
            ]
        )

    def _fallback_patterns(
        self,
        categories: list[dict],
        total_spent: float,
        monthly_limit: float,
        non_essential_total: float,
        expenses: list[dict],
    ) -> list[str]:
        patterns = []
        top_cat = categories[0]["category"] if categories else None
        if top_cat:
            patterns.append(f"Highest spending in {top_cat}: ${categories[0]['total']:.2f}")

        non_ess_pct = (non_essential_total / total_spent * 100) if total_spent > 0 else 0
        if non_ess_pct > 50:
            patterns.append(f"{non_ess_pct:.1f}% of spending is non-essential")

        if total_spent > monthly_limit * 0.8:
            patterns.append(f"Approaching monthly limit ({(total_spent / monthly_limit * 100):.1f}% used)")

        if len(categories) >= 5:
            patterns.append("Highly diversified spending across multiple categories")

        high_single = [expense for expense in expenses if expense["amount"] > monthly_limit * 0.15]
        if high_single:
            patterns.append(f"{len(high_single)} expense(s) exceed 15% of monthly budget individually")
        return patterns

    async def run(self, state: ExpenseGraphState) -> dict:
        expenses = state["expenses"]
        monthly_limit = state["monthly_limit"]
        logger.info("PatternAgent: analyzing patterns")

        total_spent = sum(e["amount"] for e in expenses)
        essential_total = sum(e["amount"] for e in expenses if e.get("is_essential"))
        non_essential_total = total_spent - essential_total

        category_map = defaultdict(lambda: {"total": 0.0, "count": 0})
        for e in expenses:
            cat = e.get("category", "Other")
            category_map[cat]["total"] += e["amount"]
            category_map[cat]["count"] += 1

        categories = [
            {"category": k, "total": round(v["total"], 2), "count": v["count"]}
            for k, v in sorted(category_map.items(), key=lambda x: -x[1]["total"])
        ]

        patterns = self._fallback_patterns(categories, total_spent, monthly_limit, non_essential_total, expenses)
        summary = {
            "monthly_limit": monthly_limit,
            "total_spent": round(total_spent, 2),
            "essential_total": round(essential_total, 2),
            "non_essential_total": round(non_essential_total, 2),
            "categories": categories,
            "expense_count": len(expenses),
        }

        try:
            llm_result = await self.gemini.ainvoke_structured(
                self.prompt,
                self.parser,
                summary_json=json.dumps(summary, indent=2),
            )
            if llm_result.patterns:
                patterns = llm_result.patterns
        except Exception as exc:
            logger.warning(f"PatternAgent: falling back to deterministic patterns: {exc}")

        result = {
            "total_spent": round(total_spent, 2),
            "essential_total": round(essential_total, 2),
            "non_essential_total": round(non_essential_total, 2),
            "categories": categories,
            "patterns": patterns,
        }

        logger.info(f"PatternAgent: total=${total_spent:.2f}, essential=${essential_total:.2f}")
        return result
