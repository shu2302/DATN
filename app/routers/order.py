from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import OrderCreate
from jose import jwt
from app.core.security import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Header(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/")
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    total_price = 0

    # tạo order trước
    new_order = Order(total_price=0)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # xử lý từng item
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()

        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        if product.quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}")

        # tính tiền
        total_price += product.price * item.quantity

        # trừ tồn kho
        product.quantity -= item.quantity

        # tạo order item
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity
        )

        db.add(order_item)

    # cập nhật tổng tiền
    new_order.total_price = total_price

    db.commit()
    db.refresh(new_order)

    return {
        "order_id": new_order.id,
        "total_price": total_price
    }