from typing import TypedDict

from backend.models.schemas import ExpenseItem


class ExpenseGraphState(TypedDict, total=False):
    raw_expenses: list[ExpenseItem]
    monthly_limit: float
    expenses: list[dict]
    ingestion_errors: list[dict]
    total_raw: int
    total_spent: float
    essential_total: float
    non_essential_total: float
    categories: list[dict]
    patterns: list[str]
    alerts: list[dict]
    suggestions: list[str]
    risk_score: float

