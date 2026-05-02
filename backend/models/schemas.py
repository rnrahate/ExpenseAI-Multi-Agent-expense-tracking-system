from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
import re


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    password: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^\+?[1-9]\d{9,14}$", v):
            raise ValueError("Invalid phone number")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def at_least_one(cls, v, info):
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    first_name: str
    email: str


class ExpenseItem(BaseModel):
    description: str
    amount: float
    category: Optional[str] = None
    date: Optional[str] = None


class AnalyzeRequest(BaseModel):
    expenses: List[ExpenseItem]
    monthly_limit: float


class CategoryBreakdown(BaseModel):
    category: str
    total: float
    count: int


class Alert(BaseModel):
    type: str
    message: str
    severity: str  # low, medium, high


class AnalyzeResponse(BaseModel):
    total_spent: float
    monthly_limit: float
    remaining_budget: float
    essential_total: float
    non_essential_total: float
    categories: List[CategoryBreakdown]
    alerts: List[Alert]
    suggestions: List[str]
    risk_score: float
    patterns: List[str]
    classified_expenses: List[dict]
