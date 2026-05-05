from typing import List

from langgraph.graph import END, START, StateGraph

from backend.agents.ingestion_agent import IngestionAgent
from backend.agents.classification_agent import ClassificationAgent
from backend.agents.pattern_agent import PatternAgent
from backend.agents.risk_agent import RiskAgent
from backend.agents.suggestion_agent import SuggestionAgent
from backend.agents.state import ExpenseGraphState
from backend.logger import setup_logger
from backend.models.schemas import Alert, AnalyzeResponse, CategoryBreakdown, ExpenseItem

logger = setup_logger(__name__)


class Orchestrator:
    """Coordinates the LangGraph-based multi-agent expense analysis workflow."""

    def __init__(self):
        self.ingestion = IngestionAgent()
        self.classification = ClassificationAgent()
        self.pattern = PatternAgent()
        self.risk = RiskAgent()
        self.suggestion = SuggestionAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(ExpenseGraphState)
        workflow.add_node("ingestion", self.ingestion.run)
        workflow.add_node("classification", self.classification.run)
        workflow.add_node("pattern", self.pattern.run)
        workflow.add_node("risk", self.risk.run)
        workflow.add_node("suggestion", self.suggestion.run)

        workflow.add_edge(START, "ingestion")
        workflow.add_conditional_edges(
            "ingestion",
            self._route_after_ingestion,
            {
                "classification": "classification",
                "end": END,
            },
        )
        workflow.add_edge("classification", "pattern")
        workflow.add_edge("pattern", "risk")
        workflow.add_edge("risk", "suggestion")
        workflow.add_edge("suggestion", END)
        return workflow.compile()

    def _route_after_ingestion(self, state: ExpenseGraphState) -> str:
        return "classification" if state.get("expenses") else "end"

    async def run(self, expenses: List[ExpenseItem], monthly_limit: float) -> AnalyzeResponse:
        logger.info("Orchestrator: starting LangGraph pipeline")
        state = await self.graph.ainvoke(
            {
                "raw_expenses": expenses,
                "monthly_limit": monthly_limit,
            }
        )

        if not state.get("expenses"):
            logger.warning("Orchestrator: no valid expenses after ingestion")
            return AnalyzeResponse(
                total_spent=0, monthly_limit=monthly_limit, remaining_budget=monthly_limit,
                essential_total=0, non_essential_total=0, categories=[], alerts=[],
                suggestions=["No valid expenses to analyze."], risk_score=0, patterns=[], classified_expenses=[]
            )

        logger.info("Orchestrator: LangGraph pipeline complete")

        return AnalyzeResponse(
            total_spent=state["total_spent"],
            monthly_limit=state["monthly_limit"],
            remaining_budget=round(state["monthly_limit"] - state["total_spent"], 2),
            essential_total=state["essential_total"],
            non_essential_total=state["non_essential_total"],
            categories=[CategoryBreakdown(**c) for c in state["categories"]],
            alerts=[Alert(**a) for a in state["alerts"]],
            suggestions=state["suggestions"],
            risk_score=state["risk_score"],
            patterns=state["patterns"],
            classified_expenses=state["expenses"],
        )
