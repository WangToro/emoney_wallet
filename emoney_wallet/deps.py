from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from db import SessionLocal
from models import User
from config import SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.hash import bcrypt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
    return user

def verify_pin(pin_input: str, user: User, db: Session):
    if user.is_pin_locked:
        raise HTTPException(403, detail="Your PIN is locked due to multiple failed attempts.")

    if not user.pin_code or not bcrypt.verify(pin_input, user.pin_code):
        user.pin_fail_count += 1
        if user.pin_fail_count >= 3:
            user.is_pin_locked = True
        db.commit()
        raise HTTPException(403, detail="Invalid PIN code.")

    # 驗證成功時，清除錯誤紀錄
    user.pin_fail_count = 0
    db.commit()