from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET ALL USERS
@router.get("/")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()