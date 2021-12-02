from pydantic import BaseModel
from datetime import datetime


class Chore(BaseModel):
    id: int
    chore_name: str
    last_tracked_time: datetime
    next_estimated_execution_time: datetime
    next_execution_assigned_to_user_id: int