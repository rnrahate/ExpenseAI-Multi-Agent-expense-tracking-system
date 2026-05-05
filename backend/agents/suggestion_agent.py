import json

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)

from backend.agents.output_models import SuggestionResponseModel
from backend.agents.state import ExpenseGraphState
from backend.logger import setup_logger
from backend.services.gemini_service import GeminiService

logger = setup_logger(__name__)


class SuggestionAgent:
    """Generates personalized financial suggestions with a dedicated LangChain prompt."""

    def __init__(self):
        self.gemini = GeminiService()
        self.parser = PydanticOutputParser(pydantic_object=SuggestionResponseModel)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """You are SuggestionAgent inside a LangGraph personal finance workflow.

Actions to perform:
1. Review the user's spending summary, patterns, alerts, and risk score.
2. Produce exactly 4 practical and actionable suggestions.
3. Prioritize budget control, habit change, and near-term next steps.
4. Keep each suggestion concise and specific.
5. Return only structured output that follows the schema instructions.

{format_instructions}"""
                    )
                ),
                HumanMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """Financial summary:
{summary_json}"""
                    )
                ),
            ]
        )

    async def run(self, state: ExpenseGraphState) -> dict:
        logger.info("SuggestionAgent: generating suggestions")

        top_cats = [c["category"] for c in state.get("categories", [])[:3]]
        summary = {
            "total_spent": state["total_spent"],
            "monthly_limit": state["monthly_limit"],
            "essential": state["essential_total"],
            "non_essential": state["non_essential_total"],
            "top_categories": top_cats,
            "risk_score": state["risk_score"],
            "patterns": state.get("patterns", []),
            "alerts": state.get("alerts", []),
        }

        suggestions = [
            "Review your non-essential spending",
            "Set category-wise budgets",
            "Track daily expenses",
            "Build an emergency fund",
        ]
        try:
            llm_result = await self.gemini.ainvoke_structured(
                self.prompt,
                self.parser,
                summary_json=json.dumps(summary, indent=2),
            )
            if llm_result.suggestions:
                suggestions = llm_result.suggestions[:4]
        except Exception as exc:
            logger.warning(f"SuggestionAgent: using fallback suggestions: {exc}")

        logger.info(f"SuggestionAgent: generated {len(suggestions)} suggestions")
        return {"suggestions": suggestions}
