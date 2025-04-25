from fastapi import APIRouter, Depends, HTTPException
from db import SessionLocal
from models import User, Wallet, Transaction
from schemas.merchant import  MerchantChargeRequest, ManualRefundRequest, RefundByTransactionRequest
from sqlalchemy.orm import Session
from sqlalchemy import or_
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from deps import get_db, get_current_user

router = APIRouter()


@router.post("/merchant/charge")
def merchant_charge(
    data: MerchantChargeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 確認當前帳號是商戶
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Only merchants can charge customers")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # 查詢付款者
    payer = db.query(User).filter(User.username == data.from_username).first()
    if not payer:
        raise HTTPException(status_code=404, detail="Payer user not found")

    payer_wallet = db.query(Wallet).filter(Wallet.user_id == payer.id).first()
    merchant_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()

    if payer_wallet.balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance in payer's wallet")

    # 扣款 & 收款
    payer_wallet.balance -= data.amount
    merchant_wallet.balance += data.amount

    # 加入交易紀錄
    transaction = Transaction(
        from_user_id=payer.id,
        to_user_id=current_user.id,
        amount=data.amount,
        type="charge"
    )
    db.add(transaction)
    db.commit()

    return {
        "message": f"Charged {data.amount} from {data.from_username}",
        "new_merchant_balance": merchant_wallet.balance
    }

@router.get("/merchant/records")
def get_merchant_records(
    type: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 確認是商戶
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Only merchants can view charge records")

    query = db.query(Transaction).filter(
        or_(
            Transaction.to_user_id == current_user.id,
            Transaction.from_user_id == current_user.id
        )
    )
    if type:
        query = query.filter(Transaction.type == type)
    
    records = query.order_by(Transaction.timestamp.desc()).all()

    result = []
    for tx in records:
        result.append({
            "from_user_id": tx.from_user_id,
            "to_user_id": tx.to_user_id,
            "amount": tx.amount,
            "type": tx.type,
            "timestamp": tx.timestamp.isoformat()
        })

    return result

@router.post("/merchant/refund")
def refund_to_customer(
    data: ManualRefundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_merchant:
        raise HTTPException(status_code=403, detail="Only merchants can issue refunds")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Refund amount must be positive")

    customer = db.query(User).filter(User.username == data.to_username).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    merchant_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    customer_wallet = db.query(Wallet).filter(Wallet.user_id == customer.id).first()

    if merchant_wallet.balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance for refund")

    # 扣款與退回
    merchant_wallet.balance -= data.amount
    customer_wallet.balance += data.amount

    # 建立 refund 紀錄
    transaction = Transaction(
        from_user_id=current_user.id,
        to_user_id=customer.id,
        amount=data.amount,
        type="refund"
    )
    db.add(transaction)
    db.commit()

    return {
        "message": f"Refunded {data.amount} to {data.to_username}",
        "new_merchant_balance": merchant_wallet.balance
    }


@router.post("/merchant/refund/by-transaction")
def refund_by_transaction(
    data: RefundByTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_merchant:
        raise HTTPException(403, detail="Only merchants can refund")

    original_tx = db.query(Transaction).filter(Transaction.id == data.transaction_id).first()
    if not original_tx or original_tx.type != "charge":
        raise HTTPException(404, detail="Original charge transaction not found")

    if original_tx.to_user_id != current_user.id:
        raise HTTPException(403, detail="You are not the receiver of this transaction")

    # 檢查是否已退款
    existing_refund = db.query(Transaction).filter(
        Transaction.type == "refund",
        Transaction.from_user_id == original_tx.to_user_id,
        Transaction.to_user_id == original_tx.from_user_id,
        Transaction.amount == original_tx.amount
    ).first()
    if existing_refund:
        raise HTTPException(400, detail="Already refunded")

    merchant_wallet = db.query(Wallet).filter(Wallet.user_id == current_user.id).first()
    customer_wallet = db.query(Wallet).filter(Wallet.user_id == original_tx.from_user_id).first()

    if merchant_wallet.balance < original_tx.amount:
        raise HTTPException(400, detail="Insufficient balance to refund")

    merchant_wallet.balance -= original_tx.amount
    customer_wallet.balance += original_tx.amount

    refund_tx = Transaction(
        from_user_id=current_user.id,
        to_user_id=original_tx.from_user_id,
        amount=original_tx.amount,
        type="refund"
    )
    db.add(refund_tx)
    db.commit()

    return {
        "message": "Refund completed successfully",
        "refund_id": refund_tx.id
    }
