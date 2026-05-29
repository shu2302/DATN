from __future__ import annotations

from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database.database import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.product_combo import ProductCombo, ProductComboItem
from app.models.activity_log import ActivityLog

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"

router = APIRouter(prefix="/combos", tags=["Combos"])

# Schemas
class ComboCreate(BaseModel):
    name:         str
    discount_pct: float = 5.0
    product_ids:  list[int]

class ComboUpdate(BaseModel):
    name:         Optional[str]   = None
    discount_pct: Optional[float] = None
    is_active:    Optional[bool]  = None
    product_ids:  Optional[list[int]] = None

# HELPER — Serialize combo
def _combo_resp(c: ProductCombo) -> dict:
    products = []
    for item in c.items:
        if item.product:
            products.append({
                "product_id": item.product_id,
                "name":       item.product.name,
                "price":      item.product.price,
            })
    total_original = sum(p["price"] for p in products)
    total_discounted = round(total_original * (1 - c.discount_pct / 100), 0)
    return {
        "id":               c.id,
        "name":             c.name,
        "discount_pct":     c.discount_pct,
        "is_active":        c.is_active,
        "products":         products,
        "total_original":   total_original,
        "total_discounted": total_discounted,
        "saved":            round(total_original - total_discounted, 0),
        "created_at":       c.created_at,
    }


# GET /combos/ — Tất cả combo
@router.get("/")
def get_combos(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    combos = db.query(ProductCombo).filter(ProductCombo.is_active == True).all()
    return [_combo_resp(c) for c in combos]

@router.get("/all")
def get_all_combos(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    combos = db.query(ProductCombo).all()
    return [_combo_resp(c) for c in combos]


# POST /combos/ — Tạo combo thủ công

@router.post("/")
def create_combo(
    data: ComboCreate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    if len(data.product_ids) < 2:
        raise HTTPException(400, "Combo phải có ít nhất 2 sản phẩm")
    if not (0 < data.discount_pct < 100):
        raise HTTPException(400, "% giảm giá phải từ 0.1 đến 99.9")

    # Kiểm tra sản phẩm hợp lệ
    for pid in data.product_ids:
        if not db.query(Product).filter(Product.id == pid).first():
            raise HTTPException(404, f"Không tìm thấy sản phẩm ID {pid}")

    combo = ProductCombo(
        name         = data.name,
        discount_pct = data.discount_pct,
        created_by   = admin["user_id"],
    )
    db.add(combo)
    db.flush()

    for pid in data.product_ids:
        db.add(ProductComboItem(combo_id=combo.id, product_id=pid))

    db.add(ActivityLog(
        user_id=admin["user_id"], action="create_combo",
        detail=f"Tạo combo '{data.name}' giảm {data.discount_pct}%"
    ))
    db.commit()
    db.refresh(combo)
    return _combo_resp(combo)


# PUT /combos/{id} — Sửa combo (Admin)

@router.put("/{combo_id}")
def update_combo(
    combo_id: int,
    data: ComboUpdate,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    combo = db.query(ProductCombo).filter(ProductCombo.id == combo_id).first()
    if not combo:
        raise HTTPException(404, "Không tìm thấy combo")

    if data.name         is not None: combo.name         = data.name
    if data.discount_pct is not None: combo.discount_pct = data.discount_pct
    if data.is_active    is not None: combo.is_active    = data.is_active

    if data.product_ids is not None:
        if len(data.product_ids) < 2:
            raise HTTPException(400, "Combo phải có ít nhất 2 sản phẩm")
        # Xóa items cũ, thêm mới
        db.query(ProductComboItem).filter(ProductComboItem.combo_id == combo_id).delete()
        for pid in data.product_ids:
            db.add(ProductComboItem(combo_id=combo_id, product_id=pid))

    db.commit()
    db.refresh(combo)
    return _combo_resp(combo)


# DELETE /combos/{id} — Xóa combo (Admin)

@router.delete("/{combo_id}")
def delete_combo(
    combo_id: int,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    combo = db.query(ProductCombo).filter(ProductCombo.id == combo_id).first()
    if not combo:
        raise HTTPException(404, "Không tìm thấy combo")
    db.delete(combo)
    db.commit()
    return {"message": "Đã xóa combo"}


# GET /combos/ai-suggest — AI gợi ý combo dựa trên lịch sử mua

@router.get("/ai-suggest")
async def ai_suggest_combos(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):

    orders_with_items = (
        db.query(Order.id)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .group_by(Order.id)
        .having(func.count(OrderItem.id) >= 2)
        .all()
    )
    order_ids = [o.id for o in orders_with_items]

    if len(order_ids) < 3:
        return {
            "suggestions": [],
            "message": "Chưa đủ dữ liệu để gợi ý combo (cần ít nhất 3 đơn hàng có nhiều sản phẩm)",
        }

    co_occur: dict[tuple, int] = {}
    product_names: dict[int, str] = {}

    for oid in order_ids:
        items = (
            db.query(OrderItem.product_id, Product.name)
            .join(Product, OrderItem.product_id == Product.id)
            .filter(OrderItem.order_id == oid)
            .all()
        )
        pids = [i.product_id for i in items]
        for i in items:
            product_names[i.product_id] = i.name

        for a in range(len(pids)):
            for b in range(a + 1, len(pids)):
                pair = tuple(sorted([pids[a], pids[b]]))
                co_occur[pair] = co_occur.get(pair, 0) + 1

    top_pairs = sorted(co_occur.items(), key=lambda x: x[1], reverse=True)[:5]

    triple_occur: dict[tuple, int] = {}
    for oid in order_ids:
        items = db.query(OrderItem.product_id).filter(OrderItem.order_id == oid).all()
        pids = sorted([i.product_id for i in items])
        if len(pids) >= 3:
            for a in range(len(pids)):
                for b in range(a + 1, len(pids)):
                    for c in range(b + 1, len(pids)):
                        triple = (pids[a], pids[b], pids[c])
                        triple_occur[triple] = triple_occur.get(triple, 0) + 1

    top_triples = sorted(triple_occur.items(), key=lambda x: x[1], reverse=True)[:3]

    raw_suggestions = []
    for pair, count in top_pairs:
        names = [product_names.get(pid, f"SP#{pid}") for pid in pair]
        prices = []
        for pid in pair:
            p = db.query(Product.price).filter(Product.id == pid).first()
            prices.append(p[0] if p else 0)
        raw_suggestions.append({
            "product_ids":    list(pair),
            "product_names":  names,
            "co_buy_count":   count,
            "total_price":    sum(prices),
            "suggested_discount": 5.0 if count < 5 else (8.0 if count < 10 else 10.0),
        })

    for triple, count in top_triples:
        names = [product_names.get(pid, f"SP#{pid}") for pid in triple]
        prices = []
        for pid in triple:
            p = db.query(Product.price).filter(Product.id == pid).first()
            prices.append(p[0] if p else 0)
        raw_suggestions.append({
            "product_ids":    list(triple),
            "product_names":  names,
            "co_buy_count":   count,
            "total_price":    sum(prices),
            "suggested_discount": 10.0 if count < 3 else 12.0,
        })

    data_str = "\n".join([
        f"- {s['product_names']} (mua cùng {s['co_buy_count']} lần, tổng giá {s['total_price']:,.0f}đ)"
        for s in raw_suggestions
    ])

    prompt = (
        "Bạn là AI quản lý siêu thị. Đặt tên combo hấp dẫn cho các nhóm sản phẩm sau.\n"
        "Trả lời JSON array, mỗi phần tử có: combo_name (string), reason (string ngắn).\n"
        "Chỉ trả JSON, không giải thích.\n\n"
        f"Danh sách:\n{data_str}\n\nJSON:"
    )

    combo_names = [None] * len(raw_suggestions)
    combo_reasons = [None] * len(raw_suggestions)

    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            res = await c.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.4}},
            )
            if res.status_code == 200:
                raw = res.json().get("response", "").strip()
                # Clean JSON
                import re, json as _json
                m = re.search(r"\[.*\]", raw, re.DOTALL)
                if m:
                    parsed = _json.loads(m.group())
                    for i, item in enumerate(parsed[:len(raw_suggestions)]):
                        combo_names[i]   = item.get("combo_name")
                        combo_reasons[i] = item.get("reason")
    except Exception:
        pass

    for i, s in enumerate(raw_suggestions):
        if not combo_names[i]:
            combo_names[i] = " + ".join(s["product_names"][:2])
        s["suggested_name"]   = combo_names[i]
        s["suggested_reason"] = combo_reasons[i] or "Khách hàng thường mua cùng nhau"

    return {
        "suggestions":   raw_suggestions,
        "total_orders_analyzed": len(order_ids),
        "message": f"Phân tích từ {len(order_ids)} đơn hàng",
    }


# POST /combos/check-discount — Tính giảm giá khi tạo đơn hàng

class CheckComboRequest(BaseModel):
    product_ids: list[int]

@router.post("/check-discount")
def check_combo_discount(
    req: CheckComboRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):

    input_set   = set(req.product_ids)
    active_combos = db.query(ProductCombo).filter(ProductCombo.is_active == True).all()

    matched = []
    for combo in active_combos:
        combo_pids = {item.product_id for item in combo.items}
        if combo_pids.issubset(input_set):
            total_original   = sum(item.product.price for item in combo.items if item.product)
            total_discounted = round(total_original * (1 - combo.discount_pct / 100), 0)
            matched.append({
                "combo_id":       combo.id,
                "combo_name":     combo.name,
                "discount_pct":   combo.discount_pct,
                "products":       [item.product.name for item in combo.items if item.product],
                "original_price": total_original,
                "discounted_price": total_discounted,
                "saved":          round(total_original - total_discounted, 0),
            })

    total_saved = sum(m["saved"] for m in matched)
    return {
        "matched_combos": matched,
        "total_saved":    total_saved,
        "has_discount":   len(matched) > 0,
    }
