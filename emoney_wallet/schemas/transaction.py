from pydantic import BaseModel
from datetime import datetime

class TransactionRecord(BaseModel):
    id: int
    from_user_id: int
    to_user_id: int
    amount: float
    timestamp: datetime
    type: str

    class Config:
        from_attributes = True
