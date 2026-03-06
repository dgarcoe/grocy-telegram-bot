from pydantic import BaseModel
from typing import List
from datetime import datetime


class Expense(BaseModel):
    id: int
    description: str
    amount: float
    paid_by: str
    participants: List[str]
    created_at: datetime
