from collections import defaultdict
from backend.logger import setup_logger

logger = setup_logger(__name__)


class PatternAgent:
    """Detects spending patterns from classified expenses."""

    def run(self, data: dict) -> dict:
        expenses = data["expenses"]
        monthly_limit = data["monthly_limit"]
        logger.info("PatternAgent: analyzing patterns")

        total_spent = sum(e["amount"] for e in expenses)
        essential_total = sum(e["amount"] for e in expenses if e.get("is_essential"))
        non_essential_total = total_spent - essential_total

        category_map = defaultdict(lambda: {"total": 0.0, "count": 0})
        for e in expenses:
            cat = e.get("category", "Other")
            category_map[cat]["total"] += e["amount"]
            category_map[cat]["count"] += 1

        categories = [
            {"category": k, "total": round(v["total"], 2), "count": v["count"]}
            for k, v in sorted(category_map.items(), key=lambda x: -x[1]["total"])
        ]

        patterns = []
        top_cat = categories[0]["category"] if categories else None
        if top_cat:
            patterns.append(f"Highest spending in {top_cat}: ${categories[0]['total']:.2f}")

        non_ess_pct = (non_essential_total / total_spent * 100) if total_spent > 0 else 0
        if non_ess_pct > 50:
            patterns.append(f"{non_ess_pct:.1f}% of spending is non-essential")

        if total_spent > monthly_limit * 0.8:
            patterns.append(f"Approaching monthly limit ({(total_spent/monthly_limit*100):.1f}% used)")

        if len(categories) >= 5:
            patterns.append("Highly diversified spending across multiple categories")

        high_single = [e for e in expenses if e["amount"] > monthly_limit * 0.15]
        if high_single:
            patterns.append(f"{len(high_single)} expense(s) exceed 15% of monthly budget individually")

        data.update({
            "total_spent": round(total_spent, 2),
            "essential_total": round(essential_total, 2),
            "non_essential_total": round(non_essential_total, 2),
            "categories": categories,
            "patterns": patterns,
        })

        logger.info(f"PatternAgent: total=${total_spent:.2f}, essential=${essential_total:.2f}")
        return data
