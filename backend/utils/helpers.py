from datetime import datetime


def current_timestamp() -> str:
    return datetime.utcnow().isoformat()


def format_currency(amount: float) -> str:
    return f"${amount:,.2f}"


def pct(part: float, total: float) -> float:
    return round((part / total * 100), 1) if total > 0 else 0.0
