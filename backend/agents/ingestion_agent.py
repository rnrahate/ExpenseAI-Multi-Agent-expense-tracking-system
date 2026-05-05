import json
from typing import List

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)

from backend.agents.output_models import IngestionResponseModel
from backend.agents.state import ExpenseGraphState
from backend.logger import setup_logger
from backend.models.schemas import ExpenseItem
from backend.services.gemini_service import GeminiService
from backend.utils.validators import validate_expense

logger = setup_logger(__name__)


class IngestionAgent:
    """Validates and normalizes raw expense data with prompt-guided cleanup."""

    def __init__(self):
        self.gemini = GeminiService()
        self.parser = PydanticOutputParser(pydantic_object=IngestionResponseModel)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """You are IngestionAgent inside a LangGraph-based personal finance workflow.

Actions to perform:
1. Preserve the exact order and count of the provided validated expenses.
2. Normalize each description into a concise user-friendly label.
3. Keep every amount aligned with the provided record and do not invent new expenses.
4. Keep category as "Uncategorized" when there is not enough evidence to improve it.
5. Keep date as provided, or "Unknown" when missing.
6. Return only structured data that follows the schema instructions.

{format_instructions}"""
                    )
                ),
                HumanMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """Monthly budget limit: {monthly_limit}

Validated expenses to normalize:
{expenses_json}"""
                    )
                ),
            ]
        )

    def _fallback_ingest(self, expenses: List[ExpenseItem], monthly_limit: float) -> dict:
        logger.info(f"IngestionAgent: processing {len(expenses)} expenses")
        cleaned = []
        errors = []

        for i, exp in enumerate(expenses):
            is_valid, msg = validate_expense(exp)
            if not is_valid:
                errors.append({"index": i, "error": msg})
                logger.warning(f"Invalid expense at index {i}: {msg}")
                continue
            cleaned.append({
                "description": exp.description.strip(),
                "amount": round(abs(exp.amount), 2),
                "category": exp.category or "Uncategorized",
                "date": exp.date or "Unknown",
                "is_essential": False,
                "classified": False
            })

        logger.info(f"IngestionAgent: {len(cleaned)} valid, {len(errors)} invalid")
        return {
            "expenses": cleaned,
            "monthly_limit": monthly_limit,
            "ingestion_errors": errors,
            "total_raw": len(expenses)
        }

    async def run(self, state: ExpenseGraphState) -> dict:
        raw_expenses = state["raw_expenses"]
        monthly_limit = state["monthly_limit"]
        baseline = self._fallback_ingest(raw_expenses, monthly_limit)

        if not baseline["expenses"]:
            return baseline

        try:
            llm_result = await self.gemini.ainvoke_structured(
                self.prompt,
                self.parser,
                monthly_limit=monthly_limit,
                expenses_json=json.dumps(baseline["expenses"], indent=2),
            )
            if len(llm_result.expenses) != len(baseline["expenses"]):
                raise ValueError("IngestionAgent returned a mismatched expense count")

            merged = []
            for base_expense, llm_expense in zip(baseline["expenses"], llm_result.expenses):
                merged.append(
                    {
                        **base_expense,
                        "description": llm_expense.description.strip() or base_expense["description"],
                        "category": llm_expense.category or base_expense["category"],
                        "date": llm_expense.date or base_expense["date"],
                    }
                )

            baseline["expenses"] = merged
            logger.info("IngestionAgent: prompt-guided normalization complete")
        except Exception as exc:
            logger.warning(f"IngestionAgent: falling back to deterministic normalization: {exc}")

        return baseline
