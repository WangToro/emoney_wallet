from pydantic import BaseModel
from enum import Enum
from fastapi import HTTPException

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserInfoExtended(BaseModel):
    id: int
    username: str
    balance: float
    is_merchant: bool
    kyc_status: str

    model_config = {
         "from_attributes" : True
    }

class KYCStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"

class KYCUpdateRequest(BaseModel):
    status: KYCStatus

class MerchantStatusUpdateRequest(BaseModel):
    is_merchant: bool

class PinInput(BaseModel):
    pin: str  

def validate_pin_format(pin: str):
    if not pin.isdigit():
        raise HTTPException(400, detail="PIN must be numeric")
    if len(pin) < 4 or len(pin) > 10:
        raise HTTPException(400, detail="PIN length must be between 4 and 10 digits")