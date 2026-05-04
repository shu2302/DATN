import csv, io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.product import Product
from app.models.activity_log import ActivityLog
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.core.security import get_current_user, require_admin

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductResponse])
def get_products(search: str = "", min_price: float = 0, max_price: float = 1e9,
                 category_id: int = None, current_user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    q = db.query(Product)
    if search: q = q.filter(Product.name.contains(search))
    if category_id: q = q.filter(Product.category_id == category_id)
    q = q.filter(Product.price >= min_price, Product.price <= max_price)
    return q.all()


@router.get("/low-stock", response_model=list[ProductResponse])
def get_low_stock(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [p for p in products if p.quantity <= p.low_stock_threshold]


@router.get("/export-csv")
def export_csv(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    products = db.query(Product).all()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID", "Tên sản phẩm", "Giá", "Số lượng", "Danh mục", "Ngày nhập"])
    for p in products:
        w.writerow([p.id, p.name, p.price, p.quantity,
                    p.category.name if p.category else "", p.import_date])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=products.csv"})


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p: raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    return p


@router.post("/", response_model=ProductResponse)
def create_product(data: ProductCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    p = Product(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    db.add(ActivityLog(user_id=current_user["user_id"], action="create_product", detail=f"Thêm: {p.name}"))
    db.commit()
    return p


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, current_user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p: raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    db.add(ActivityLog(user_id=current_user["user_id"], action="update_product", detail=f"Sửa ID {product_id}"))
    db.commit()
    return p


@router.delete("/{product_id}")
def delete_product(product_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p: raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    db.add(ActivityLog(user_id=admin["user_id"], action="delete_product", detail=f"Xóa: {p.name}"))
    db.delete(p)
    db.commit()
    return {"message": "Đã xóa sản phẩm"}
