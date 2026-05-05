from typing import List

from pydantic import BaseModel, Field

from backend.models.schemas import Alert


class NormalizedExpense(BaseModel):
    description: str
    amount: float
    category: str = "Uncategorized"
    date: str = "Unknown"
    is_essential: bool = False
    classified: bool = False
    classification_method: str = "pending"
    reason: str = ""
    is_harmful: bool = False


class IngestionIssue(BaseModel):
    index: int
    error: str


class IngestionResponseModel(BaseModel):
    expenses: List[NormalizedExpense] = Field(default_factory=list)
    ingestion_errors: List[IngestionIssue] = Field(default_factory=list)


class ExpenseClassification(BaseModel):
    category: str
    is_essential: bool
    is_harmful: bool = False
    reason: str


class ClassificationResponseModel(BaseModel):
    decisions: List[ExpenseClassification] = Field(default_factory=list)


class PatternResponseModel(BaseModel):
    patterns: List[str] = Field(default_factory=list)


class RiskResponseModel(BaseModel):
    risk_score: float = 0.0
    alerts: List[Alert] = Field(default_factory=list)


class SuggestionResponseModel(BaseModel):
    suggestions: List[str] = Field(default_factory=list)

