from pydantic import BaseModel

class MerchantChargeRequest(BaseModel):
    from_username: str
    amount: float

class RefundRequest(BaseModel):
    to_username: str
    amount: float

class ManualRefundRequest(BaseModel):
    to_username: str
    amount: float

class RefundByTransactionRequest(BaseModel):
    transaction_id: int
