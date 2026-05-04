from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse
from app.core.security import get_current_user, require_admin

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryResponse])
def get_categories(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Category).all()


@router.post("/", response_model=CategoryResponse)
def create_category(data: CategoryCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.name == data.name).first():
        raise HTTPException(status_code=400, detail="Danh mục đã tồn tại")
    cat = Category(name=data.name, description=data.description)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{cat_id}", response_model=CategoryResponse)
def update_category(cat_id: int, data: CategoryCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")
    cat.name = data.name
    cat.description = data.description
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{cat_id}")
def delete_category(cat_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")
    db.delete(cat)
    db.commit()
    return {"message": "Đã xóa danh mục"}
