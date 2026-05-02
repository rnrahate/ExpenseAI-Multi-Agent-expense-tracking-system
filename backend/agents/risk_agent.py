from backend.logger import setup_logger

logger = setup_logger(__name__)

HARMFUL_KEYWORDS = ["alcohol", "casino", "gambling", "bet", "lottery", "tobacco", "cigarette", "vape", "drugs"]


class RiskAgent:
    """Evaluates financial risk and flags harmful expenses."""

    def run(self, data: dict) -> dict:
        expenses = data["expenses"]
        total_spent = data["total_spent"]
        monthly_limit = data["monthly_limit"]
        non_essential_total = data["non_essential_total"]
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
        data["alerts"] = alerts
        data["risk_score"] = risk_score
        data["expenses"] = expenses

        logger.info(f"RiskAgent: risk_score={risk_score}, alerts={len(alerts)}")
        return data
