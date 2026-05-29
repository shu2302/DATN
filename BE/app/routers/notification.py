from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database.database import get_db
from app.models.activity_log import ActivityLog
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.stock_import import StockImport

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# HELPER — tính tốc độ bán (units/ngày) trong 7 ngày qua

def _compute_sell_rates(db: Session) -> dict[int, float]:
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    rows = (
        db.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label("total_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .filter(func.date(Order.created_at) >= cutoff)
        .group_by(OrderItem.product_id)
        .all()
    )
    return {r.product_id: r.total_sold / 7.0 for r in rows}


def _days_until_stockout(quantity: int, rate: float) -> Optional[int]:
    if rate <= 0:
        return None
    return int(quantity / rate)



# ENDPOINT 1 — Thông báo tồn kho

@router.get("/")
def get_notifications(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sell_rates = _compute_sell_rates(db)
    notifications = []
    products = db.query(Product).all()

    for p in products:
        rate = sell_rates.get(p.id, 0.0)
        days_left = _days_until_stockout(p.quantity, rate)

        if p.quantity == 0:
            notifications.append({
                "type": "out_of_stock", "level": "danger",
                "message": f"'{p.name}' đã HẾT HÀNG!",
                "product_id": p.id, "product_name": p.name,
                "current_qty": 0, "sell_rate": rate,
            })

        elif p.quantity <= p.low_stock_threshold:
            notifications.append({
                "type": "low_stock", "level": "warning",
                "message": f"'{p.name}' sắp hết hàng (còn {p.quantity}, ngưỡng {p.low_stock_threshold})",
                "product_id": p.id, "product_name": p.name,
                "current_qty": p.quantity, "sell_rate": round(rate, 2),
                "days_left": days_left,
            })

        elif days_left is not None and days_left <= 3 and rate > 0:
            notifications.append({
                "type": "predicted_out", "level": "warning",
                "message": (
                    f"'{p.name}' dự đoán HẾT HÀNG trong ~{days_left} ngày "
                    f"(tốc độ bán {rate:.1f} sản phẩm/ngày, còn {p.quantity})"
                ),
                "product_id": p.id, "product_name": p.name,
                "current_qty": p.quantity, "sell_rate": round(rate, 2),
                "days_left": days_left,
            })

        if p.quantity > 50 and sell_rates.get(p.id, 0) == 0:
            notifications.append({
                "type": "slow_moving", "level": "info",
                "message": f"'{p.name}' tồn {p.quantity} nhưng chưa bán được trong 7 ngày",
                "product_id": p.id, "product_name": p.name,
                "current_qty": p.quantity, "sell_rate": 0.0,
            })

    return {"count": len(notifications), "notifications": notifications}



# ENDPOINT 2 — AI Agent: Dự đoán lượng cần nhập

@router.get("/ai-import-suggestions")
def get_import_suggestions(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    sell_rates = _compute_sell_rates(db)
    products   = db.query(Product).all()

    last_prices = {}
    for p in products:
        last = (
            db.query(StockImport.import_price)
            .filter(StockImport.product_id == p.id)
            .order_by(StockImport.created_at.desc())
            .first()
        )
        last_prices[p.id] = last[0] if last else round(p.price * 0.65, 0)  # fallback: 65% giá bán

    suggestions = []
    for p in products:
        rate      = sell_rates.get(p.id, 0.0)
        days_left = _days_until_stockout(p.quantity, rate)
        needs_import = False
        reason = ""

        if p.quantity == 0:
            needs_import = True
            reason = "Hết hàng hoàn toàn"
        elif p.quantity <= p.low_stock_threshold:
            needs_import = True
            reason = f"Dưới ngưỡng cảnh báo (còn {p.quantity}/{p.low_stock_threshold})"
        elif days_left is not None and days_left <= 3 and rate > 0:
            needs_import = True
            reason = f"AI dự đoán hết hàng trong {days_left} ngày"

        if needs_import:
            target_qty  = max(10, int(rate * 14) + p.low_stock_threshold - p.quantity)
            import_price = last_prices.get(p.id, round(p.price * 0.65, 0))

            suggestions.append({
                "product_id":    p.id,
                "product_name":  p.name,
                "current_qty":   p.quantity,
                "sell_rate":     round(rate, 2),
                "days_left":     days_left,
                "reason":        reason,
                "suggested_qty": target_qty,
                "suggested_price": import_price,
                "estimated_cost": target_qty * import_price,
            })

    total_cost = sum(s["estimated_cost"] for s in suggestions)

    return {
        "suggestions":  suggestions,
        "total_items":  len(suggestions),
        "total_cost":   total_cost,
        "generated_at": date.today().isoformat(),
    }



# ENDPOINT 3 — Agentic Auto-Import: Admin xác nhận nhập hàng

class AutoImportItem(BaseModel):
    product_id:    int
    quantity:      int
    import_price:  float
    supplier:      Optional[str] = "AI Auto-Import"
    note:          Optional[str] = None

class AutoImportRequest(BaseModel):
    items: list[AutoImportItem]

@router.post("/ai-import-confirm")
def confirm_auto_import(
    req: AutoImportRequest,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not req.items:
        raise HTTPException(status_code=400, detail="Danh sách nhập rỗng")

    created = []
    total_cost = 0.0

    for item in req.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy SP ID {item.product_id}")
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Số lượng phải > 0")

        cost   = item.quantity * item.import_price
        record = StockImport(
            product_id   = item.product_id,
            quantity     = item.quantity,
            import_price = item.import_price,
            total_cost   = cost,
            supplier     = item.supplier or "AI Auto-Import",
            note         = item.note or f"Tự động nhập bởi AI Agent ngày {date.today()}",
            imported_by  = admin["user_id"],
        )
        db.add(record)
        product.quantity += item.quantity
        total_cost += cost
        created.append((record, product.name))

    db.flush()

    for record, pname in created:
        db.add(ActivityLog(
            user_id = admin["user_id"],
            action  = "ai_auto_import",
            detail  = (
                f"[AI Agent] Nhập {record.quantity} '{pname}' "
                f"| Giá: {record.import_price:,.0f}đ "
                f"| Tổng: {record.total_cost:,.0f}đ"
            ),
        ))

    db.commit()
    for record, _ in created:
        db.refresh(record)

    return {
        "message":     f"AI Agent đã nhập hàng thành công {len(created)} sản phẩm",
        "total_items": len(created),
        "total_cost":  total_cost,
        "records": [
            {
                "product_name": pname,
                "quantity":     r.quantity,
                "import_price": r.import_price,
                "total_cost":   r.total_cost,
            }
            for r, pname in created
        ],
    }



# ENDPOINT 4 — AI Report Summary

@router.get("/ai-report-summary")
async def get_ai_report_summary(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    today  = date.today()
    week_start = today - timedelta(days=7)

    rev_q = (
        db.query(func.sum(Order.total_price), func.count(Order.id))
        .filter(func.date(Order.created_at) >= week_start.isoformat())
        .first()
    )
    revenue_week = float(rev_q[0] or 0)
    orders_week  = int(rev_q[1] or 0)

    prev_start = today - timedelta(days=14)
    rev_prev = db.query(func.sum(Order.total_price)).filter(
        and_(
            func.date(Order.created_at) >= prev_start.isoformat(),
            func.date(Order.created_at) < week_start.isoformat(),
        )
    ).scalar() or 0
    revenue_change_pct = (
        ((revenue_week - float(rev_prev)) / float(rev_prev) * 100)
        if rev_prev > 0 else 0
    )

    top3 = (
        db.query(Product.name, func.sum(OrderItem.quantity).label("sold"))
        .join(OrderItem, Product.id == OrderItem.product_id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(func.date(Order.created_at) >= week_start.isoformat())
        .group_by(Product.id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(3).all()
    )

    sell_rates  = _compute_sell_rates(db)
    need_import = [
        p.name for p in db.query(Product).all()
        if p.quantity == 0 or p.quantity <= p.low_stock_threshold
    ]

    data = {
        "period":         f"{week_start} đến {today}",
        "revenue_week":   revenue_week,
        "orders_week":    orders_week,
        "revenue_change": round(revenue_change_pct, 1),
        "top_products":   [{"name": r.name, "sold": int(r.sold)} for r in top3],
        "need_import":    need_import[:5],
        "slow_moving":    [
            p.name for p in db.query(Product).all()
            if p.quantity > 20 and sell_rates.get(p.id, 0) == 0
        ][:3],
    }

    prompt = f"""Bạn là AI trợ lý quản lý siêu thị. Tóm tắt tình hình kinh doanh TUẦN NÀY dựa trên dữ liệu thực.
Viết bằng tiếng Việt, ngắn gọn, rõ ràng, giống như báo cáo thực. Không bịa thêm số liệu.

DỮ LIỆU:
{json.dumps(data, ensure_ascii=False, indent=2)}

Viết báo cáo tóm tắt gồm:
1. Kết quả kinh doanh tuần này (doanh thu, đơn hàng, so sánh tuần trước)
2. Top sản phẩm bán chạy
3. Cảnh báo tồn kho cần chú ý
4. Đề xuất ngắn gọn cho tuần tới
Giữ trong 150-200 từ."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            res = await c.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.3}},
            )
            if res.status_code == 200:
                summary = res.json().get("response", "").strip()
                return {"summary": summary, "source": "llm", "data": data}
    except httpx.ConnectError:
        pass

    change_sign = "+" if revenue_change_pct >= 0 else ""
    top_str = ", ".join([f"{r['name']} ({r['sold']} cái)" for r in data["top_products"]])
    import_str = ", ".join(need_import[:3]) if need_import else "Không có"
    summary = (
        f"📊 Báo cáo tuần {week_start} – {today}\n\n"
        f"💰 Doanh thu: {revenue_week:,.0f}đ ({change_sign}{revenue_change_pct:.1f}% so với tuần trước)\n"
        f"📦 Số đơn hàng: {orders_week}\n\n"
        f"🏆 Top sản phẩm: {top_str}\n\n"
        f"⚠️ Cần nhập hàng: {import_str}\n\n"
        f"💡 Đề xuất: {'Duy trì chiến lược hiện tại.' if revenue_change_pct >= 0 else 'Xem xét khuyến mãi để tăng doanh thu.'}"
    )
    return {"summary": summary, "source": "rule-based", "data": data}
