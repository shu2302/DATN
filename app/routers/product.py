from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse
from jose import jwt
from app.core.security import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/products", tags=["Products"])


def get_current_user(token: str = Header(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# CREATE
@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    new_product = Product(
        name=product.name,
        price=product.price,
        quantity=product.quantity
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


# READ ALL
@router.get("/", response_model=list[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    return db.query(Product).all()


# READ BY ID
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# UPDATE
@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, updated: ProductCreate, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.name = updated.name
    product.price = updated.price
    product.quantity = updated.quantity

    db.commit()
    db.refresh(product)
    return product


# DELETE
@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return {"message": "Deleted successfully"}