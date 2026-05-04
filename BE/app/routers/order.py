import csv, io
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.database.database import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.activity_log import ActivityLog
from app.schemas.order import OrderCreate, OrderResponse
from app.core.security import get_current_user

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse)
def create_order(order: OrderCreate, current_user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    total_price = 0
    new_order = Order(total_price=0, user_id=current_user["user_id"])
    try:
        db.add(new_order)
        db.flush()
        for item in order.items:
            product = db.query(Product).filter(Product.id == item.product_id).with_for_update().first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm ID {item.product_id}")
            if product.quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"'{product.name}' không đủ hàng (còn {product.quantity})")
            total_price += product.price * item.quantity
            product.quantity -= item.quantity
            db.add(OrderItem(order_id=new_order.id, product_id=item.product_id,
                             quantity=item.quantity, unit_price=product.price))
        new_order.total_price = total_price
        db.commit()
    except Exception as e:
        db.rollback(); raise e
    db.refresh(new_order)
    db.add(ActivityLog(user_id=current_user["user_id"], action="create_order",
                       detail=f"Đơn #{new_order.id} — {total_price:,.0f}đ"))
    db.commit()
    return new_order


@router.get("/")
def get_orders(start_date: Optional[date] = Query(None),
               end_date:   Optional[date] = Query(None),
               current_user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    q = db.query(Order).order_by(Order.created_at.desc())
    if start_date:
        q = q.filter(func.date(Order.created_at) >= start_date.isoformat())
    if end_date:
        q = q.filter(func.date(Order.created_at) <= end_date.isoformat())
    orders = q.all()
    return [{"id": o.id, "total_price": o.total_price, "status": o.status,
             "user_id": o.user_id, "created_at": o.created_at, "items": []} for o in orders]


@router.get("/dashboard")
def dashboard(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).all()
    items  = db.query(OrderItem).all()
    revenue, order_count = {}, {}
    for o in orders:
        day = o.created_at.date().isoformat()
        revenue[day]     = revenue.get(day, 0) + o.total_price
        order_count[day] = order_count.get(day, 0) + 1
    return {"revenue": revenue, "orders_per_day": order_count,
            "total_revenue": sum(revenue.values()), "total_orders": len(orders)}


@router.get("/top-products")
def top_products(limit: int = 10, current_user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    result = (db.query(Product.id, Product.name, func.sum(OrderItem.quantity).label("total_sold"))
              .join(OrderItem, Product.id == OrderItem.product_id)
              .group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(limit).all())
    return [{"product_id": r.id, "name": r.name, "total_sold": r.total_sold} for r in result]


@router.get("/slow-products")
def slow_products(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    sold_map = {r.product_id: r.total for r in
                db.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("total"))
                .group_by(OrderItem.product_id).all()}
    return sorted([{"id": p.id, "name": p.name, "quantity": p.quantity,
                    "total_sold": sold_map.get(p.id, 0)}
                   for p in db.query(Product).filter(Product.quantity > 0).all()],
                  key=lambda x: x["total_sold"])[:20]


@router.get("/revenue-by-category")
def revenue_by_category(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.category import Category
    result = (db.query(Category.name,
                       func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"))
              .join(Product, Product.category_id == Category.id)
              .join(OrderItem, OrderItem.product_id == Product.id)
              .group_by(Category.id).all())
    return [{"category": r.name, "revenue": r.revenue or 0} for r in result]


@router.get("/export-csv")
def export_csv(start_date: Optional[date] = Query(None),
               end_date:   Optional[date] = Query(None),
               current_user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    q = db.query(Order).order_by(Order.created_at.desc())
    if start_date:
        q = q.filter(func.date(Order.created_at) >= start_date.isoformat())
    if end_date:
        q = q.filter(func.date(Order.created_at) <= end_date.isoformat())
    orders = q.all()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID", "Tổng tiền", "Trạng thái", "Ngày tạo"])
    for o in orders:
        w.writerow([o.id, o.total_price, o.status, o.created_at])
    out.seek(0)
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=orders.csv"})


@router.get("/{order_id}")
def get_order_detail(order_id: int, current_user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return {"id": order.id, "total_price": order.total_price, "status": order.status,
            "created_at": order.created_at,
            "items": [{"product_id": i.product_id,
                       "product_name": i.product.name if i.product else "",
                       "quantity": i.quantity, "unit_price": i.unit_price} for i in order.items]}
