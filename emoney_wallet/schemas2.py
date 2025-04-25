from pydantic import BaseModel
from enum import Enum

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class BalanceResponse(BaseModel):
    balance: float

class DepositRequest(BaseModel):
    amount: float

class TransferRequest(BaseModel):
    to_username: str
    amount: float

class DepositRequest(BaseModel):
    amount: float

class TransferRequest(BaseModel):
    to_username: str
    amount: float

class UserInfoExtended(BaseModel):
    id: int
    username: str
    balance: float
    is_merchant: bool
    kyc_status: str

    class Config:
        orm_mode = True

class KYCStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"

class KYCUpdateRequest(BaseModel):
    status: KYCStatus

class MerchantStatusUpdateRequest(BaseModel):
    is_merchant: bool

class MerchantChargeRequest(BaseModel):
    from_username: str
    amount: float
