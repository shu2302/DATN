from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.schemas.user import UserCreate, UserLogin, UserUpdate, UserResponse
from app.core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username đã tồn tại")
    if user.email and db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email đã tồn tại")
    new_user = User(
        username=user.username,
        password=hash_password(user.password),
        email=user.email,
        full_name=user.full_name,
        role=user.role if user.role in ["admin", "staff"] else "staff"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.add(ActivityLog(user_id=new_user.id, action="register", detail=f"Đăng ký tài khoản: {new_user.username}"))
    db.commit()
    return new_user


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")
    if not db_user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị vô hiệu hóa")
    token = create_access_token({"sub": db_user.username, "user_id": db_user.id, "role": db_user.role})
    db.add(ActivityLog(user_id=db_user.id, action="login", detail=f"Đăng nhập thành công"))
    db.commit()
    return {
        "access_token": token,
        "user": {"id": db_user.id, "username": db_user.username, "role": db_user.role,
                 "full_name": db_user.full_name, "email": db_user.email}
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    return user


@router.put("/me", response_model=UserResponse)
def update_me(updates: UserUpdate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    if updates.email: user.email = updates.email
    if updates.full_name: user.full_name = updates.full_name
    if updates.password: user.password = hash_password(updates.password)
    db.commit()
    db.refresh(user)
    db.add(ActivityLog(user_id=user.id, action="update_profile", detail="Cập nhật thông tin cá nhân"))
    db.commit()
    return user
