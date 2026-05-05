import json

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)

from backend.agents.output_models import RiskResponseModel
from backend.agents.state import ExpenseGraphState
from backend.logger import setup_logger
from backend.services.gemini_service import GeminiService

logger = setup_logger(__name__)

HARMFUL_KEYWORDS = ["alcohol", "casino", "gambling", "bet", "lottery", "tobacco", "cigarette", "vape", "drugs"]


class RiskAgent:
    """Evaluates financial risk with deterministic facts and prompt-guided alert reasoning."""

    def __init__(self):
        self.gemini = GeminiService()
        self.parser = PydanticOutputParser(pydantic_object=RiskResponseModel)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """You are RiskAgent inside a LangGraph personal finance workflow.

Actions to perform:
1. Review the calculated spending risk facts.
2. Assign a risk score from 0.0 to 10.0.
3. Produce concise alerts with type, message, and severity using only low, medium, or high.
4. Base your reasoning only on the provided facts and do not invent transactions.
5. Return only structured output that follows the schema instructions.

{format_instructions}"""
                    )
                ),
                HumanMessagePromptTemplate(
                    prompt=PromptTemplate.from_template(
                        """Risk facts:
{risk_facts_json}"""
                    )
                ),
            ]
        )

    def _fallback_risk(
        self,
        expenses: list[dict],
        total_spent: float,
        monthly_limit: float,
        non_essential_total: float,
    ) -> tuple[list[dict], float, list[dict]]:
        logger.info("RiskAgent: evaluating risk")

        alerts = []
        risk_score = 0.0

        # Over-budget alert
        if total_spent > monthly_limit:
            overage = total_spent - monthly_limit
            alerts.append({
                "type": "budget_exceeded",
                "message": f"Monthly limit exceeded by ${overage:.2f}!",
                "severity": "high"
            })
            risk_score += 3.0
        elif total_spent > monthly_limit * 0.9:
            alerts.append({
                "type": "budget_warning",
                "message": f"Warning: {(total_spent/monthly_limit*100):.1f}% of monthly budget used",
                "severity": "medium"
            })
            risk_score += 1.5

        # Non-essential ratio
        ness_ratio = non_essential_total / total_spent if total_spent > 0 else 0
        if ness_ratio > 0.6:
            alerts.append({
                "type": "high_non_essential",
                "message": f"{ness_ratio*100:.1f}% of spending is non-essential. Consider cutting back.",
                "severity": "medium"
            })
            risk_score += 2.0
        elif ness_ratio > 0.4:
            risk_score += 1.0

        # Harmful expenses
        harmful = []
        for e in expenses:
            desc = e["description"].lower()
            if any(kw in desc for kw in HARMFUL_KEYWORDS):
                harmful.append(e["description"])
                e["is_harmful"] = True
                risk_score += 1.0
            else:
                e["is_harmful"] = False

        if harmful:
            alerts.append({
                "type": "harmful_expenses",
                "message": f"Detected {len(harmful)} potentially harmful expense(s): {', '.join(harmful[:3])}",
                "severity": "high"
            })

        # Large single transactions
        large_txns = [e for e in expenses if e["amount"] > monthly_limit * 0.2]
        if large_txns:
            alerts.append({
                "type": "large_transaction",
                "message": f"{len(large_txns)} transaction(s) exceed 20% of your monthly budget",
                "severity": "low"
            })
            risk_score += 0.5

        risk_score = min(round(risk_score, 1), 10.0)
        return alerts, risk_score, expenses

    async def run(self, state: ExpenseGraphState) -> dict:
        expenses = [dict(expense) for expense in state["expenses"]]
        total_spent = state["total_spent"]
        monthly_limit = state["monthly_limit"]
        non_essential_total = state["non_essential_total"]
        alerts, risk_score, expenses = self._fallback_risk(expenses, total_spent, monthly_limit, non_essential_total)

        harmful_expenses = [expense["description"] for expense in expenses if expense.get("is_harmful")]
        risk_facts = {
            "total_spent": total_spent,
            "monthly_limit": monthly_limit,
            "non_essential_total": non_essential_total,
            "non_essential_ratio": round(non_essential_total / total_spent, 4) if total_spent else 0,
            "harmful_expenses": harmful_expenses,
            "large_transaction_count": len([expense for expense in expenses if expense["amount"] > monthly_limit * 0.2]),
            "fallback_risk_score": risk_score,
            "fallback_alerts": alerts,
        }

        try:
            llm_result = await self.gemini.ainvoke_structured(
                self.prompt,
                self.parser,
                risk_facts_json=json.dumps(risk_facts, indent=2),
            )
            risk_score = min(max(round(llm_result.risk_score, 1), 0.0), 10.0)
            alerts = [alert.model_dump() for alert in llm_result.alerts]
        except Exception as exc:
            logger.warning(f"RiskAgent: falling back to deterministic risk rules: {exc}")

        logger.info(f"RiskAgent: risk_score={risk_score}, alerts={len(alerts)}")
        return {
            "alerts": alerts,
            "risk_score": risk_score,
            "expenses": expenses,
        }
