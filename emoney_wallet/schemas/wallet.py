from pydantic import BaseModel

class BalanceResponse(BaseModel):
    balance: float

class DepositRequest(BaseModel):
    amount: float

class TransferRequest(BaseModel):
    to_username: str
    amount: float

class TransferRequest(BaseModel):
    to_username: str
    amount: float
    pin: str  