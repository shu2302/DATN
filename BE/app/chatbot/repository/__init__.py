"""
Repository layer — tất cả SQLAlchemy queries.
Không chứa business logic, chỉ truy vấn thuần túy.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.stock_import import StockImport
from app.models.user import User


# ── Helper ────────────────────────────────────────────────────
def _date_filter(q, model, sd: Optional[date], ed: Optional[date]):
    if sd and ed:
        q = q.filter(and_(
            func.date(model.created_at) >= sd.isoformat(),
            func.date(model.created_at) <= ed.isoformat(),
        ))
    return q


# ══════════════════════════════════════════════════════════════
# REVENUE
# ══════════════════════════════════════════════════════════════
def get_revenue(db: Session, sd: Optional[date], ed: Optional[date]) -> dict[str, Any]:
    q = db.query(func.sum(Order.total_price), func.count(Order.id))
    q = _date_filter(q, Order, sd, ed)
    total_rev, total_cnt = q.first()
    total_rev = float(total_rev or 0)
    total_cnt = int(total_cnt or 0)

    daily_q = (
        db.query(
            func.date(Order.created_at).label("day"),
            func.sum(Order.total_price).label("revenue"),
            func.count(Order.id).label("cnt"),
        )
        .group_by(func.date(Order.created_at))
        .order_by(desc(func.date(Order.created_at)))
    )
    daily_q = _date_filter(daily_q, Order, sd, ed)

    return {
        "total_revenue": total_rev,
        "total_orders":  total_cnt,
        "avg_per_order": round(total_rev / total_cnt, 0) if total_cnt else 0,
        "daily": [
            {"date": str(r.day), "revenue": float(r.revenue or 0), "orders": int(r.cnt)}
            for r in daily_q.limit(30).all()
        ],
    }


# ══════════════════════════════════════════════════════════════
# ORDERS (with full item detail)
# ══════════════════════════════════════════════════════════════
def get_orders(db: Session, sd: Optional[date], ed: Optional[date]) -> dict[str, Any]:
    count_q = db.query(func.count(Order.id), func.sum(Order.total_price))
    count_q = _date_filter(count_q, Order, sd, ed)
    total_cnt, total_rev = count_q.first()
    total_cnt = int(total_cnt or 0)

    orders_q = db.query(Order).order_by(desc(Order.created_at))
    orders_q = _date_filter(orders_q, Order, sd, ed)
    orders   = orders_q.limit(20).all()

    order_list = []
    for o in orders:
        items = [
            {
                "product":   it.product.name if it.product else "?",
                "qty":       it.quantity,
                "unit_price": it.unit_price,
                "subtotal":  round(it.quantity * it.unit_price, 0),
            }
            for it in o.items
        ]
        order_list.append({
            "id":         o.id,
            "total":      o.total_price,
            "status":     o.status,
            "created_at": o.created_at.strftime("%d/%m/%Y %H:%M"),
            "items":      items,
        })

    return {
        "total_orders":   total_cnt,
        "total_revenue":  float(total_rev or 0),
        "orders":         order_list,
    }


# ══════════════════════════════════════════════════════════════
# STOCK
# ══════════════════════════════════════════════════════════════
def get_stock(db: Session) -> dict[str, Any]:
    prods = db.query(Product).all()
    out_of  = [{"id": p.id, "name": p.name} for p in prods if p.quantity == 0]
    low     = [{"id": p.id, "name": p.name, "quantity": p.quantity,
                "threshold": p.low_stock_threshold}
               for p in prods if 0 < p.quantity <= p.low_stock_threshold]
    ok      = [{"id": p.id, "name": p.name, "quantity": p.quantity}
               for p in prods if p.quantity > p.low_stock_threshold]
    return {
        "total_products": len(prods),
        "ok_count":       len(ok),
        "low_stock":      low,
        "out_of_stock":   out_of,
        "ok_products":    ok[:15],
    }


# ══════════════════════════════════════════════════════════════
# TOP PRODUCTS
# ══════════════════════════════════════════════════════════════
def get_top_products(
    db: Session, sd: Optional[date], ed: Optional[date], limit: int = 10
) -> dict[str, Any]:
    q = (
        db.query(
            Product.id, Product.name, Product.price,
            func.sum(OrderItem.quantity).label("sold"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("rev"),
        )
        .join(OrderItem, Product.id == OrderItem.product_id)
        .join(Order,     OrderItem.order_id == Order.id)
    )
    q = _date_filter(q, Order, sd, ed)
    tops = (
        q.group_by(Product.id)
         .order_by(desc(func.sum(OrderItem.quantity)))
         .limit(limit)
         .all()
    )
    return {
        "top_products": [
            {
                "rank":          i + 1,
                "name":          r.name,
                "price":         r.price,
                "total_sold":    int(r.sold),
                "total_revenue": float(r.rev or 0),
            }
            for i, r in enumerate(tops)
        ]
    }


# ══════════════════════════════════════════════════════════════
# SLOW PRODUCTS
# ══════════════════════════════════════════════════════════════
def get_slow_products(db: Session) -> dict[str, Any]:
    sub = (
        db.query(OrderItem.product_id, func.sum(OrderItem.quantity).label("sold"))
        .group_by(OrderItem.product_id)
        .subquery()
    )
    rows = (
        db.query(
            Product.id, Product.name, Product.quantity,
            Product.price, Product.import_date,
            func.coalesce(sub.c.sold, 0).label("sold"),
        )
        .outerjoin(sub, Product.id == sub.c.product_id)
        .filter(Product.quantity > 0)
        .order_by(func.coalesce(sub.c.sold, 0))
        .limit(20)
        .all()
    )
    return {
        "slow_products": [
            {
                "name":        r.name,
                "quantity":    r.quantity,
                "price":       r.price,
                "total_sold":  int(r.sold),
                "import_date": str(r.import_date)[:10] if r.import_date else "",
            }
            for r in rows
        ]
    }


# ══════════════════════════════════════════════════════════════
# STOCK IMPORTS
# ══════════════════════════════════════════════════════════════
def get_imports(db: Session, sd: Optional[date], ed: Optional[date]) -> dict[str, Any]:
    q = (
        db.query(
            StockImport.id, StockImport.quantity,
            StockImport.import_price, StockImport.total_cost,
            StockImport.supplier, StockImport.created_at,
            Product.name.label("product_name"),
        )
        .join(Product, StockImport.product_id == Product.id)
    )
    q    = _date_filter(q, StockImport, sd, ed)
    recs = q.order_by(desc(StockImport.created_at)).limit(30).all()

    total_cost = float(db.query(func.sum(StockImport.total_cost)).scalar() or 0)
    total_qty  = int(db.query(func.sum(StockImport.quantity)).scalar() or 0)

    return {
        "total_import_cost":  total_cost,
        "total_imported_qty": total_qty,
        "records": [
            {
                "id":           r.id,
                "product":      r.product_name,
                "quantity":     r.quantity,
                "import_price": r.import_price,
                "total_cost":   r.total_cost,
                "supplier":     r.supplier or "Không ghi",
                "date":         r.created_at.strftime("%d/%m/%Y"),
            }
            for r in recs
        ],
    }


# ══════════════════════════════════════════════════════════════
# PRODUCT INFO  (semantic-aware: exact match > partial > all)
# ══════════════════════════════════════════════════════════════
def get_product_info(db: Session, message: str, semantic_names: list[str] | None = None) -> dict[str, Any]:
    """
    semantic_names: tên SP từ RAG layer (nếu có).
    """
    msg_lower = message.lower()
    all_prods = db.query(Product).all()

    # Ưu tiên 1: semantic names từ RAG
    if semantic_names:
        matched = [p for p in all_prods
                   if any(sn.lower() in p.name.lower() or p.name.lower() in sn.lower()
                          for sn in semantic_names)]
    else:
        matched = []

    # Ưu tiên 2: exact substring match
    if not matched:
        matched = [p for p in all_prods if p.name.lower() in msg_lower]

    # Ưu tiên 3: word-level partial match (từ >= 3 ký tự)
    if not matched:
        matched = [
            p for p in all_prods
            if any(w in msg_lower for w in p.name.lower().split() if len(w) >= 3)
        ]

    # Fallback: trả tất cả (giới hạn 20)
    show_all = not matched
    if show_all:
        matched = all_prods[:20]

    return {
        "products": [
            {
                "name":          p.name,
                "price":         p.price,
                "quantity":      p.quantity,
                "category":      p.category.name if p.category else "Chưa phân loại",
                "import_date":   p.import_date.strftime("%d/%m/%Y") if p.import_date else "",
                "low_threshold": p.low_stock_threshold,
                "status": (
                    "Hết hàng"
                    if p.quantity == 0 else
                    f"Sắp hết (còn {p.quantity})"
                    if p.quantity <= p.low_stock_threshold else
                    f"Còn hàng ({p.quantity})"
                ),
            }
            for p in matched[:20]
        ],
        "show_all": show_all,
    }


# ══════════════════════════════════════════════════════════════
# CATEGORY
# ══════════════════════════════════════════════════════════════
def get_categories(db: Session) -> dict[str, Any]:
    cats = (
        db.query(Category.id, Category.name, func.count(Product.id).label("cnt"))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id)
        .all()
    )
    rev_rows = (
        db.query(
            Category.name,
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("rev"),
        )
        .join(Product, Product.category_id == Category.id)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Category.id)
        .all()
    )
    rev_map = {r.name: float(r.rev or 0) for r in rev_rows}

    return {
        "categories": [
            {"name": c.name, "product_count": c.cnt, "revenue": rev_map.get(c.name, 0)}
            for c in cats
        ]
    }


# ══════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════
def get_users(db: Session) -> dict[str, Any]:
    users = db.query(User).all()
    return {
        "total_users": len(users),
        "users": [
            {
                "id":         u.id,
                "username":   u.username,
                "full_name":  u.full_name or "",
                "role":       u.role,
                "is_active":  u.is_active,
                "created_at": u.created_at.strftime("%d/%m/%Y"),
            }
            for u in users
        ],
    }


# ══════════════════════════════════════════════════════════════
# USER ANALYTICS  (ai mua nhiều, doanh thu theo user)
# ══════════════════════════════════════════════════════════════
def get_user_analytics(
    db: Session, sd: Optional[date], ed: Optional[date]
) -> dict[str, Any]:
    q = (
        db.query(
            User.id, User.username, User.full_name,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_price).label("total_spent"),
        )
        .join(Order, Order.user_id == User.id)
    )
    q = _date_filter(q, Order, sd, ed)
    rows = (
        q.group_by(User.id)
         .order_by(desc(func.sum(Order.total_price)))
         .all()
    )
    return {
        "user_analytics": [
            {
                "rank":         i + 1,
                "username":     r.username,
                "full_name":    r.full_name or "",
                "order_count":  int(r.order_count),
                "total_spent":  float(r.total_spent or 0),
            }
            for i, r in enumerate(rows)
        ]
    }


# ══════════════════════════════════════════════════════════════
# PRODUCT SALES BY DAY  (sản phẩm bán theo ngày)
# ══════════════════════════════════════════════════════════════
def get_product_by_day(
    db: Session,
    sd: Optional[date],
    ed: Optional[date],
    message: str,
    semantic_names: list[str] | None = None,
) -> dict[str, Any]:
    """
    Thống kê số lượng + doanh thu theo ngày cho từng sản phẩm.
    Nếu câu hỏi đề cập tên SP cụ thể → lọc theo SP đó.
    """
    msg_lower = message.lower()
    all_prods = db.query(Product).all()

    # Xác định sản phẩm cần lọc
    if semantic_names:
        target = [p for p in all_prods
                  if any(sn.lower() in p.name.lower() for sn in semantic_names)]
    else:
        target = [p for p in all_prods if p.name.lower() in msg_lower]
        if not target:
            target = [p for p in all_prods
                      if any(w in msg_lower for w in p.name.lower().split() if len(w) >= 3)]

    product_ids = [p.id for p in target] if target else None

    q = (
        db.query(
            func.date(Order.created_at).label("day"),
            Product.name.label("product_name"),
            func.sum(OrderItem.quantity).label("qty_sold"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(Product,   OrderItem.product_id == Product.id)
    )

    if product_ids:
        q = q.filter(Product.id.in_(product_ids))

    q = _date_filter(q, Order, sd, ed)

    rows = (
        q.group_by(func.date(Order.created_at), Product.id)
         .order_by(func.date(Order.created_at))
         .limit(100)
         .all()
    )

    return {
        "filter_products": [p.name for p in target] if target else ["tất cả"],
        "breakdown": [
            {
                "date":         str(r.day),
                "product":      r.product_name,
                "qty_sold":     int(r.qty_sold),
                "revenue":      float(r.revenue or 0),
            }
            for r in rows
        ],
    }
