from pydantic import BaseModel
from datetime import datetime


class Settlement(BaseModel):
    id: int
    paid_by: str
    paid_to: str
    amount: float
    created_at: datetime
