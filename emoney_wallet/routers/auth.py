from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from db import SessionLocal
from models import User, Wallet
from schemas.user import UserCreate, Token, UserInfoExtended, KYCUpdateRequest, MerchantStatusUpdateRequest, PinInput
from schemas.wallet import BalanceResponse, DepositRequest, TransferRequest
from schemas.merchant import MerchantChargeRequest, RefundRequest
from jose import jwt, JWTError
from datetime import datetime, timedelta
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from deps import get_db, get_current_user


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")




# 使用者註冊
@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # 檢查使用者是否已存在
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # 加密密碼
    hashed_password = bcrypt.hash(user.password)

    # 新增使用者
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 為使用者建立錢包（初始餘額 0）
    wallet = Wallet(user_id=new_user.id, balance=0.0)
    db.add(wallet)
    db.commit()

    return {"message": "User registered successfully"}


# 產生 JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 登入
@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if not bcrypt.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserInfoExtended)
def get_my_profile(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    wallet = db.query(Wallet).filter(Wallet.user_id == user.id).first()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "id": user.id,
        "username": user.username,
        "balance": wallet.balance,
        "is_merchant": user.is_merchant,
        "kyc_status": user.kyc_status
    }

@router.patch("/me/kyc")
def update_kyc_status(
    data: KYCUpdateRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 使用者只能提交為 pending
    if data.status != "pending":
        raise HTTPException(status_code=403, detail="Only 'pending' status can be requested")

    user.kyc_status = "pending"
    db.commit()

    return {"message": "KYC status set to pending"}

@router.post("/me/pin")
def set_or_update_pin(
    data: PinInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user.id).first()
    user.pin_code = bcrypt.hash(data.pin)
    db.commit()
    return {"message": "PIN set successfully"}

@router.post("/me/unlock-pin")
def unlock_pin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.pin_fail_count = 0
    current_user.is_pin_locked = False
    db.commit()
    return {"message": "PIN has been unlocked"}
