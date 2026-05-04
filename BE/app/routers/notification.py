from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.database import get_db
from app.models.product import Product
from app.models.order import OrderItem
from app.core.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def get_notifications(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    notifications = []
    sold_map = {r.product_id: r.total for r in
                db.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("total"))
                .group_by(OrderItem.product_id).all()}

    for p in db.query(Product).all():
        if p.quantity == 0:
            notifications.append({"type": "out_of_stock", "level": "danger",
                                   "message": f"'{p.name}' đã HẾT HÀNG!", "product_id": p.id})
        elif p.quantity <= p.low_stock_threshold:
            notifications.append({"type": "low_stock", "level": "warning",
                                   "message": f"'{p.name}' sắp hết hàng (còn {p.quantity})", "product_id": p.id})
        if p.quantity > 50 and sold_map.get(p.id, 0) == 0:
            notifications.append({"type": "slow_moving", "level": "info",
                                   "message": f"'{p.name}' tồn {p.quantity} nhưng chưa bán được",
                                   "product_id": p.id})

    return {"count": len(notifications), "notifications": notifications}
