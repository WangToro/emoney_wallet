from fastapi import APIRouter, Depends, HTTPException
from schemas.user import KYCUpdateRequest, MerchantStatusUpdateRequest
from models import User
from db import SessionLocal
from sqlalchemy.orm import Session
from deps import get_db, get_current_user

router = APIRouter()



@router.post("/admin/set-kyc")
def admin_set_kyc_status(
    username: str,
    data: KYCUpdateRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.kyc_status = data.status
    db.commit()

    return {
        "message": f"KYC status of '{username}' updated to '{data.status}'"
    }

@router.post("/admin/set-merchant")
def set_merchant_status(
    username: str,
    data: MerchantStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_merchant = data.is_merchant
    db.commit()

    status_text = "enabled" if data.is_merchant else "disabled"
    return {"message": f"Merchant status for '{username}' has been {status_text}"}