from typing import List
from models.schemas import ExpenseItem
from logger import setup_logger
from utils.validators import validate_expense

logger = setup_logger(__name__)


class IngestionAgent:
    """Validates and normalizes raw expense data."""

    def run(self, expenses: List[ExpenseItem], monthly_limit: float) -> dict:
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
