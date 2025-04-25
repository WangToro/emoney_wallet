from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_merchant = Column(Boolean, default=False)
    kyc_status = Column(String, default="not_verified")  # 可選值: not_verified / pending / verified
    pin_code = Column(String, nullable=True)
    pin_fail_count = Column(Integer, default=0)
    is_pin_locked = Column(Boolean, default=False)

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Float, default=0.0)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer)
    to_user_id = Column(Integer)
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String)
