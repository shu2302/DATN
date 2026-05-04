from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.schemas.user import UserResponse
from app.core.security import require_admin

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserResponse])
def get_all_users(admin=Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).all()


@router.put("/{user_id}/role")
def change_role(user_id: int, role: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
    if role not in ["admin", "staff"]:
        raise HTTPException(status_code=400, detail="Role không hợp lệ (admin | staff)")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    user.role = role
    db.commit()
    return {"message": f"Đã đổi role thành {role}"}


@router.put("/{user_id}/deactivate")
def deactivate_user(user_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    user.is_active = False
    db.commit()
    return {"message": "Đã vô hiệu hóa tài khoản"}


@router.get("/logs")
def get_logs(admin=Depends(require_admin), db: Session = Depends(get_db)):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(200).all()
    return [{"id": l.id, "user_id": l.user_id,
             "username": l.user.username if l.user else "—",
             "action": l.action, "detail": l.detail, "created_at": l.created_at}
            for l in logs]
