from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from db import SessionLocal
from models import User, Wallet, Transaction
from schemas.transaction import TransactionRecord
from schemas.wallet import BalanceResponse, DepositRequest, TransferRequest
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from deps import get_db, get_current_user, verify_pin


router = APIRouter()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# 查詢餘額
@router.get("/balance", response_model=BalanceResponse)
def get_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return {"balance": wallet.balance}

@router.post("/deposit")
def deposit_money(
    data: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    wallet.balance += data.amount
    transaction = Transaction(
    from_user_id=current_user.id,
    to_user_id=current_user.id,  
    amount=data.amount,
    type="deposit"
    )
    db.add(transaction)
    db.commit()
    return {"message": f"Deposited {data.amount} successfully", "new_balance": wallet.balance}

@router.post("/transfer")
def transfer_money(
    data: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_pin(data.pin, current_user, db)

    sender_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    if not sender_wallet:
        raise HTTPException(status_code=404, detail="Sender wallet not found")

    
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    if sender_wallet.balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    
    recipient_user = db.query(User).filter(User.username == data.to_username).first()
    if not recipient_user:
        raise HTTPException(status_code=404, detail="Recipient not found")

    recipient_wallet = db.query(Wallet).filter(Wallet.user_id == recipient_user.id).first()
    if not recipient_wallet:
        raise HTTPException(status_code=404, detail="Recipient wallet not found")

    
    sender_wallet.balance -= data.amount
    recipient_wallet.balance += data.amount
    transaction = Transaction(
    from_user_id=current_user.id,
    to_user_id=recipient_user.id,
    amount=data.amount,
    type="transfer"
    )
    db.add(transaction)
    db.commit()

    return {
        "message": f"Transferred {data.amount} to {data.to_username}",
        "new_balance": sender_wallet.balance
    }

@router.get("/transactions")
def get_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(
        (Transaction.from_user_id == current_user.id) |
        (Transaction.to_user_id == current_user.id)
    ).order_by(Transaction.timestamp.desc()).all()

    results = []
    for tx in txs:
        results.append({
            "type": tx.type,
            "amount": tx.amount,
            "from": tx.from_user_id,
            "to": tx.to_user_id,
            "timestamp": tx.timestamp.isoformat()
        })

    return results


@router.get("/records", response_model=list[TransactionRecord])
def get_my_transaction_records(
    type: str = Query(None, description="交易類型：transfer / charge / refund"),
    start_date: str = Query(None, description="開始日期，格式 YYYY-MM-DD"),
    end_date: str = Query(None, description="結束日期，格式 YYYY-MM-DD"),
    keyword: str = Query(None, description="對方帳號關鍵字"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)

    # 僅限相關交易
    query = query.filter(or_(
        Transaction.from_user_id == current_user.id,
        Transaction.to_user_id == current_user.id
    ))

    # 交易類型過濾
    if type:
        query = query.filter(Transaction.type == type)

    # 時間過濾
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Transaction.timestamp >= start)
        except:
            raise HTTPException(400, detail="start_date 格式錯誤")

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(Transaction.timestamp <= end)
        except:
            raise HTTPException(400, detail="end_date 格式錯誤")

    # 關鍵字搜尋 username
    if keyword:
        matched_users = db.query(User.id).filter(User.username.contains(keyword)).all()
        matched_ids = [u.id for u in matched_users]
        query = query.filter(or_(
            Transaction.from_user_id.in_(matched_ids),
            Transaction.to_user_id.in_(matched_ids)
        ))

    results = query.order_by(Transaction.timestamp.desc()).all()
    return results

@router.get("/transaction/{tx_id}", response_model=TransactionRecord)
def get_transaction_detail(
    tx_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(404, detail="Transaction not found")

    if tx.from_user_id != current_user.id and tx.to_user_id != current_user.id:
        raise HTTPException(403, detail="Unauthorized access to this transaction")

    return tx

