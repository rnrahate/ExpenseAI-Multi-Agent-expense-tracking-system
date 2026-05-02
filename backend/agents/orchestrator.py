from typing import List
from backend.models.schemas import ExpenseItem, AnalyzeResponse, CategoryBreakdown, Alert
from backend.agents.ingestion_agent import IngestionAgent
from backend.agents.classification_agent import ClassificationAgent
from backend.agents.pattern_agent import PatternAgent
from backend.agents.risk_agent import RiskAgent
from backend.agents.suggestion_agent import SuggestionAgent
from backend.logger import setup_logger

logger = setup_logger(__name__)


class Orchestrator:
    """Coordinates all agents in sequential pipeline."""

    def __init__(self):
        self.ingestion = IngestionAgent()
        self.classification = ClassificationAgent()
        self.pattern = PatternAgent()
        self.risk = RiskAgent()
        self.suggestion = SuggestionAgent()

    async def run(self, expenses: List[ExpenseItem], monthly_limit: float) -> AnalyzeResponse:
        logger.info("Orchestrator: starting pipeline")

        # Step 1: Ingest & validate
        data = self.ingestion.run(expenses, monthly_limit)

        if not data["expenses"]:
            logger.warning("Orchestrator: no valid expenses after ingestion")
            return AnalyzeResponse(
                total_spent=0, monthly_limit=monthly_limit, remaining_budget=monthly_limit,
                essential_total=0, non_essential_total=0, categories=[], alerts=[],
                suggestions=["No valid expenses to analyze."], risk_score=0, patterns=[], classified_expenses=[]
            )

        # Step 2: Classify
        data = await self.classification.run(data)

        # Step 3: Pattern detection
        data = self.pattern.run(data)

        # Step 4: Risk evaluation
        data = self.risk.run(data)

        # Step 5: Suggestions
        data = await self.suggestion.run(data)

        logger.info("Orchestrator: pipeline complete")

        return AnalyzeResponse(
            total_spent=data["total_spent"],
            monthly_limit=data["monthly_limit"],
            remaining_budget=round(data["monthly_limit"] - data["total_spent"], 2),
            essential_total=data["essential_total"],
            non_essential_total=data["non_essential_total"],
            categories=[CategoryBreakdown(**c) for c in data["categories"]],
            alerts=[Alert(**a) for a in data["alerts"]],
            suggestions=data["suggestions"],
            risk_score=data["risk_score"],
            patterns=data["patterns"],
            classified_expenses=data["expenses"],
        )
