import json

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)

from backend.logger import setup_logger
from backend.agents.output_models import ClassificationResponseModel
from backend.agents.state import ExpenseGraphState
from backend.services.gemini_service import GeminiService

logger = setup_logger(__name__)

ESSENTIAL_CATEGORIES = {"Food", "Healthcare", "Utilities", "Education", "Housing", "Transport"}
HARMFUL_KEYWORDS = ["alcohol", "casino", "gambling", "bet", "lottery", "tobacco", "cigarette", "vape", "drugs"]
RULE_BASED_KEYWORDS = {
    "Food": ["grocery", "groceries", "restaurant", "food", "meal", "lunch", "dinner", "breakfast", "coffee", "pizza", "bread", "milk"],
    "Transport": ["uber", "ola", "taxi", "bus", "metro", "petrol", "fuel", "parking", "train", "flight"],
    "Healthcare": ["medicine", "doctor", "hospital", "pharmacy", "clinic", "health", "dental", "medical"],
    "Entertainment": ["netflix", "spotify", "movie", "cinema", "game", "concert", "party", "bar", "club"],
    "Shopping": ["amazon", "flipkart", "clothes", "shoes", "fashion", "mall", "shopping"],
    "Utilities": ["electricity", "water", "gas", "internet", "wifi", "broadband", "phone bill", "recharge"],
    "Education": ["course", "book", "tuition", "school", "college", "udemy", "coursera"],
    "Housing": ["rent", "mortgage", "maintenance", "repair", "furniture"],
}


class ClassificationAgent:
    """Classifies expenses with rules first and a LangChain prompt for unresolved items."""

    def __init__(self):
        self.gemini = GeminiService()
        self.parser = PydanticOutputParser(pydantic_object=ClassificationResponseModel)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """You are ClassificationAgent inside a LangGraph personal finance workflow.

Actions to perform:
1. Classify each unresolved expense into exactly one category from:
   Food, Transport, Healthcare, Entertainment, Shopping, Utilities, Education, Housing, Other.
2. Mark whether the expense is essential for day-to-day living.
3. Mark whether the expense appears harmful or financially risky.
4. Write a short reason grounded in the description and amount.
5. Preserve the exact order and count of items.
6. Return only structured output that follows the schema instructions.

{format_instructions}"""
                    )
                ),
                HumanMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """Classify these unresolved expenses:
{expenses_json}"""
                    )
                ),
            ]
        )

    def _rule_based_classify(self, description: str) -> dict | None:
        desc_lower = description.lower()
        for category, keywords in RULE_BASED_KEYWORDS.items():
            if any(kw in desc_lower for kw in keywords):
                return {
                    "category": category,
                    "is_essential": category in ESSENTIAL_CATEGORIES,
                    "is_harmful": any(kw in desc_lower for kw in HARMFUL_KEYWORDS),
                    "reason": "Rule-based match"
                }
        return None

    def _fallback_unresolved(self, expenses: list[dict], unresolved_positions: list[int]) -> None:
        for index in unresolved_positions:
            description = expenses[index]["description"]
            desc_lower = description.lower()
            expenses[index].update(
                {
                    "category": "Other",
                    "is_essential": False,
                    "is_harmful": any(kw in desc_lower for kw in HARMFUL_KEYWORDS),
                    "reason": "Fallback classification",
                    "classified": True,
                    "classification_method": "fallback",
                }
            )

    async def run(self, state: ExpenseGraphState) -> dict:
        expenses = [dict(expense) for expense in state["expenses"]]
        logger.info(f"ClassificationAgent: classifying {len(expenses)} expenses")
        unresolved_expenses = []
        unresolved_positions = []

        for index, exp in enumerate(expenses):
            rule_result = self._rule_based_classify(exp["description"])
            if rule_result:
                exp.update(rule_result)
                exp["classified"] = True
                exp["classification_method"] = "rule"
            else:
                unresolved_positions.append(index)
                unresolved_expenses.append(
                    {
                        "description": exp["description"],
                        "amount": exp["amount"],
                        "date": exp["date"],
                    }
                )

        if unresolved_expenses:
            try:
                llm_result = await self.gemini.ainvoke_structured(
                    self.prompt,
                    self.parser,
                    expenses_json=json.dumps(unresolved_expenses, indent=2),
                )
                if len(llm_result.decisions) != len(unresolved_expenses):
                    raise ValueError("ClassificationAgent returned a mismatched decision count")

                for position, decision in zip(unresolved_positions, llm_result.decisions):
                    expenses[position].update(
                        {
                            "category": decision.category,
                            "is_essential": decision.is_essential,
                            "is_harmful": decision.is_harmful,
                            "reason": decision.reason,
                            "classified": True,
                            "classification_method": "llm",
                        }
                    )
            except Exception as exc:
                logger.warning(f"ClassificationAgent: falling back for unresolved expenses: {exc}")
                self._fallback_unresolved(expenses, unresolved_positions)

        logger.info("ClassificationAgent: classification complete")
        return {"expenses": expenses}
