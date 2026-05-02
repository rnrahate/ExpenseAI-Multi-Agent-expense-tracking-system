from models.schemas import ExpenseItem


def validate_expense(expense: ExpenseItem) -> tuple[bool, str]:
    if not expense.description or not expense.description.strip():
        return False, "Description is required"
    if expense.amount is None or expense.amount <= 0:
        return False, "Amount must be positive"
    if expense.amount > 1_000_000:
        return False, "Amount seems unrealistically large"
    return True, ""
