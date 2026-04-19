from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import OrderCreate
from jose import jwt
from app.core.security import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/orders", tags=["Orders"])


# ================= DB =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================= AUTH =================
def get_current_user(token: str = Header(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]   # ⚠️ đảm bảo sub là user_id (int) nếu DB dùng int
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


# ================= CREATE ORDER =================
@router.post("/")
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    total_price = 0

    new_order = Order(
        total_price=0,
        user_id=user
    )

    try:
        db.add(new_order)
        db.flush()  # lấy id nhưng chưa commit

        for item in order.items:
            # 🔒 lock row để tránh race condition
            product = db.query(Product) \
                .filter(Product.id == item.product_id) \
                .with_for_update() \
                .first()

            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

            if product.quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"Not enough stock for {product.name}")

            # 💰 tính tiền
            total_price += product.price * item.quantity

            # 📦 trừ tồn kho
            product.quantity -= item.quantity

            # 🧾 tạo order item
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            db.add(order_item)

        # cập nhật tổng tiền
        new_order.total_price = total_price

        db.commit()

    except Exception as e:
        db.rollback()
        raise e

    db.refresh(new_order)

    return {
        "id": new_order.id,
        "total_price": new_order.total_price,
        "created_at": new_order.created_at,
    }


# ================= GET ALL ORDERS =================
@router.get("/")
def get_orders(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()

    return [
        {
            "id": o.id,
            "total_price": o.total_price,
            "created_at": o.created_at
        }
        for o in orders
    ]

# ============dashboard ======
@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    orders = db.query(Order).all()
    items = db.query(OrderItem).all()

    revenue = {}
    order_count = {}
    product_sales = {}

    # doanh thu + số đơn
    for o in orders:
        day = o.created_at.date().isoformat()

        if day not in revenue:
            revenue[day] = 0
            order_count[day] = 0

        revenue[day] += o.total_price
        order_count[day] += 1

    # top sản phẩm
    for item in items:
        if item.product_id not in product_sales:
            product_sales[item.product_id] = 0

        product_sales[item.product_id] += item.quantity

    return {
        "revenue": revenue,
        "orders_per_day": order_count,
        "top_products": product_sales
    }

# ========top product =======
@router.get("/top-products")
def top_products(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    items = db.query(OrderItem).all()

    result = {}

    for item in items:
        if item.product_id not in result:
            result[item.product_id] = 0
        result[item.product_id] += item.quantity

    # sort giảm dần
    sorted_result = sorted(result.items(), key=lambda x: x[1], reverse=True)

    output = []

    for pid, qty in sorted_result:
        product = db.query(Product).filter(Product.id == pid).first()

        output.append({
            "product_id": pid,
            "name": product.name if product else "Unknown",
            "total_sold": qty
        })

    return output

# =========oders per day ============
@router.get("/orders-per-day")
def orders_per_day(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    orders = db.query(Order).all()

    result = {}

    for o in orders:
        day = o.created_at.date().isoformat()

        if day not in result:
            result[day] = 0

        result[day] += 1

    return result

# ================= REVENUE =================
@router.get("/revenue")
def get_revenue(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    orders = db.query(Order).all()

    result = {}

    for o in orders:
        day = o.created_at.date().isoformat()

        if day not in result:
            result[day] = 0

        result[day] += o.total_price

    return result


# ================= ORDER DETAIL =================
@router.get("/{order_id}")
def get_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

    return {
        "id": order.id,
        "total_price": order.total_price,
        "created_at": order.created_at,
        "items": [
            {
                "product_id": i.product_id,
                "quantity": i.quantity
            }
            for i in items
        ]
    }