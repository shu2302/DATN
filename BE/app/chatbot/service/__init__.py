"""
Service layer — điều phối toàn bộ pipeline:
  ParsedQuery → Cache? → DB Repo → RAG → LLM → Response
"""
from __future__ import annotations

import json, logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.chatbot.intent import Intent, ParsedQuery
from app.chatbot.cache import cache_get, cache_set
from app.chatbot.rag import semantic_search
from app.chatbot import repository as repo

logger = logging.getLogger(__name__)

OLLAMA_URL    = "http://localhost:11434/api/generate"
OLLAMA_MODEL  = "llama3.1:8b"
OLLAMA_TIMEOUT = 90.0


# ══════════════════════════════════════════════════════════════
# STRICT SYSTEM PROMPT — chống bịa tuyệt đối
# ══════════════════════════════════════════════════════════════
_SYSTEM = """Bạn là trợ lý AI của hệ thống quản lý siêu thị.

╔══════════════════════════════════════╗
║  QUY TẮC TUYỆT ĐỐI — KHÔNG NGOẠI LỆ ║
╚══════════════════════════════════════╝
1. NGUỒN DỮ LIỆU: mọi số liệu, tên, giá, ngày tháng phải lấy CHÍNH XÁC
   từ phần [DATA] bên dưới — không thêm, không đoán, không ước lượng.
2. KHÔNG CÓ DATA: chỉ nói "Không có dữ liệu để trả lời" — không bịa.
3. CÂU HỎI CHUNG (code, toán, kiến thức): trả lời tự do, không dùng [DATA].
4. NGỮ CẢNH: "ngày đó/sản phẩm đó" → tra [LỊCH SỬ]. Không rõ → hỏi lại.
5. FORMAT: Tiếng Việt, ngắn gọn, bullet nếu nhiều mục.
   Tiền: 1,000,000đ. Không in JSON thô. Không mở đầu "Dựa trên dữ liệu...".
"""


# ══════════════════════════════════════════════════════════════
# SINGLE INTENT → DB DATA
# ══════════════════════════════════════════════════════════════
def _fetch_one(intent: Intent, pq: ParsedQuery, db: Session) -> dict[str, Any]:
    """
    Lấy data cho một intent (check cache trước, query DB nếu miss).
    Trả về {"has_data", "empty_reason", "data", ...}
    """
    # ── Cache check ──────────────────────────────────────────
    cached = cache_get(intent.value, pq.period_label)
    if cached is not None:
        logger.debug(f"Cache HIT: {intent.value} / {pq.period_label}")
        return cached

    sd, ed = pq.start_date, pq.end_date

    # ── RAG: semantic search cho query mơ hồ ─────────────────
    sem_names = semantic_search(pq.raw_message, top_k=5)

    # ── Query DB ─────────────────────────────────────────────
    data: dict[str, Any]
    empty_reason = ""

    if intent == Intent.DB_REVENUE:
        data = repo.get_revenue(db, sd, ed)
        if data["total_orders"] == 0:
            empty_reason = f"Không có đơn hàng nào trong {pq.period_label}."

    elif intent == Intent.DB_ORDERS:
        data = repo.get_orders(db, sd, ed)
        if data["total_orders"] == 0:
            empty_reason = f"Không có đơn hàng nào trong {pq.period_label}."

    elif intent == Intent.DB_STOCK:
        data = repo.get_stock(db)

    elif intent == Intent.DB_TOP_PRODUCTS:
        data = repo.get_top_products(db, sd, ed)
        if not data["top_products"]:
            empty_reason = f"Chưa có dữ liệu bán hàng trong {pq.period_label}."

    elif intent == Intent.DB_SLOW_PRODUCTS:
        data = repo.get_slow_products(db)

    elif intent == Intent.DB_IMPORT:
        data = repo.get_imports(db, sd, ed)
        if not data["records"]:
            empty_reason = f"Không có phiếu nhập nào trong {pq.period_label}."

    elif intent == Intent.DB_PRODUCT_INFO:
        data = repo.get_product_info(db, pq.raw_message, sem_names)

    elif intent == Intent.DB_CATEGORY:
        data = repo.get_categories(db)

    elif intent == Intent.DB_USERS:
        data = repo.get_users(db)

    elif intent == Intent.DB_USER_ANALYTICS:
        data = repo.get_user_analytics(db, sd, ed)
        if not data["user_analytics"]:
            empty_reason = f"Không có dữ liệu người dùng trong {pq.period_label}."

    elif intent == Intent.DB_PRODUCT_BY_DAY:
        data = repo.get_product_by_day(db, sd, ed, pq.raw_message, sem_names)
        if not data["breakdown"]:
            empty_reason = f"Không có dữ liệu bán hàng trong {pq.period_label}."

    else:
        data = {}
        empty_reason = "Intent không xác định."

    result = {
        "intent":       intent.value,
        "has_data":     bool(data) and not empty_reason,
        "empty_reason": empty_reason,
        "period_label": pq.period_label,
        "data":         data,
    }

    # Cache nếu có data
    if result["has_data"]:
        cache_set(intent.value, pq.period_label, result)

    return result


# ══════════════════════════════════════════════════════════════
# MULTI-INTENT EXECUTOR
# ══════════════════════════════════════════════════════════════
def execute_multi_intent(pq: ParsedQuery, db: Session) -> dict[str, Any]:
    """
    Chạy tất cả intent trong pq.intents, merge kết quả.
    """
    if Intent.GENERAL in pq.intents:
        return {
            "intents":    [Intent.GENERAL.value],
            "has_data":   False,
            "all_results": [],
            "period_label": pq.period_label,
        }

    results: list[dict] = []
    for intent in pq.intents:
        r = _fetch_one(intent, pq, db)
        results.append(r)

    any_data = any(r["has_data"] for r in results)

    return {
        "intents":      [i.value for i in pq.intents],
        "has_data":     any_data,
        "all_results":  results,
        "period_label": pq.period_label,
    }


# ══════════════════════════════════════════════════════════════
# PRE-VALIDATE  (chặn LLM khi không có data)
# ══════════════════════════════════════════════════════════════
def pre_validate(merged: dict) -> str | None:
    """
    Trả về câu trả lời sớm (không qua LLM) nếu không có data.
    None = cho qua LLM bình thường.
    """
    if Intent.GENERAL.value in merged.get("intents", []):
        return None  # GENERAL → LLM trả lời tự do

    if not merged.get("has_data"):
        reasons = [
            r["empty_reason"]
            for r in merged.get("all_results", [])
            if r.get("empty_reason")
        ]
        if reasons:
            return "❌ " + " | ".join(reasons)
        period = merged.get("period_label", "")
        return f"❌ Không có dữ liệu{' trong ' + period if period else ''}."

    return None


# ══════════════════════════════════════════════════════════════
# FALLBACK FORMATTER  (không qua LLM)
# ══════════════════════════════════════════════════════════════
def _fmt_one(result: dict) -> str:
    """Format một intent result → string dễ đọc."""
    if not result.get("has_data"):
        return f"❌ {result.get('empty_reason', 'Không có dữ liệu.')}"

    intent = result["intent"]
    data   = result.get("data", {})
    period = result.get("period_label", "")
    lines: list[str] = []

    if intent == "DB_REVENUE":
        rev = data.get("total_revenue", 0)
        cnt = data.get("total_orders", 0)
        avg = data.get("avg_per_order", 0)
        lines.append(f"💰 Doanh thu {period}:")
        lines.append(f"  • Tổng: {rev:,.0f}đ | Đơn: {cnt} | TB/đơn: {avg:,.0f}đ")
        for d in data.get("daily", [])[:7]:
            lines.append(f"  • {d['date']}: {d['revenue']:,.0f}đ ({d['orders']} đơn)")

    elif intent == "DB_ORDERS":
        lines.append(f"🧾 Đơn hàng {period}: {data.get('total_orders',0)} đơn | {data.get('total_revenue',0):,.0f}đ")
        for o in data.get("orders", [])[:10]:
            items_str = ", ".join([f"{it['product']} ×{it['qty']}" for it in o.get("items", [])[:3]])
            lines.append(f"  • #{o['id']} — {o['total']:,.0f}đ ({o['created_at']}) [{items_str}]")

    elif intent == "DB_STOCK":
        out = data.get("out_of_stock", [])
        low = data.get("low_stock", [])
        lines.append(f"📦 Tồn kho ({data.get('total_products',0)} SP):")
        lines.append(f"  • 🟢 Đủ: {data.get('ok_count',0)} | 🟡 Sắp hết: {len(low)} | 🔴 Hết: {len(out)}")
        for p in low[:8]:
            lines.append(f"  ⚠️  {p['name']} — còn {p['quantity']} (ngưỡng {p['threshold']})")
        for p in out[:8]:
            lines.append(f"  🚫 {p['name']} — HẾT HÀNG")

    elif intent == "DB_TOP_PRODUCTS":
        lines.append(f"🏆 Top sản phẩm {period}:")
        for p in data.get("top_products", []):
            lines.append(f"  {p['rank']}. {p['name']} — {p['total_sold']} cái | {p['total_revenue']:,.0f}đ")

    elif intent == "DB_SLOW_PRODUCTS":
        lines.append("📉 Sản phẩm bán chậm:")
        for p in data.get("slow_products", [])[:10]:
            lines.append(f"  • {p['name']} — bán: {p['total_sold']} | tồn: {p['quantity']}")

    elif intent == "DB_IMPORT":
        lines.append(f"📥 Nhập hàng {period}: {data.get('total_import_cost',0):,.0f}đ | {data.get('total_imported_qty',0)} SP")
        for r in data.get("records", [])[:8]:
            lines.append(f"  • {r['date']} | {r['product']} ×{r['quantity']} | {r['import_price']:,.0f}đ | {r['supplier']}")

    elif intent == "DB_CATEGORY":
        lines.append("🗂️ Danh mục:")
        for c in data.get("categories", []):
            lines.append(f"  • {c['name']}: {c['product_count']} SP | {c['revenue']:,.0f}đ")

    elif intent == "DB_USERS":
        lines.append(f"👥 Người dùng ({data.get('total_users',0)}):")
        for u in data.get("users", []):
            flag = "✅" if u["is_active"] else "🔒"
            lines.append(f"  {flag} {u['username']} ({u['full_name']}) | {u['role']}")

    elif intent == "DB_USER_ANALYTICS":
        lines.append(f"📊 Phân tích user {period}:")
        for u in data.get("user_analytics", []):
            lines.append(f"  {u['rank']}. {u['username']} — {u['order_count']} đơn | {u['total_spent']:,.0f}đ")

    elif intent == "DB_PRODUCT_BY_DAY":
        lines.append(f"📅 Bán theo ngày {period} [{', '.join(data.get('filter_products',[]))}]:")
        for r in data.get("breakdown", [])[:15]:
            lines.append(f"  • {r['date']} | {r['product']}: {r['qty_sold']} cái | {r['revenue']:,.0f}đ")

    elif intent == "DB_PRODUCT_INFO":
        if data.get("show_all"):
            lines.append("🛍️ Danh sách sản phẩm (không tìm thấy SP cụ thể):")
        else:
            lines.append("🛍️ Thông tin sản phẩm:")
        for p in data.get("products", [])[:15]:
            lines.append(f"  • {p['name']} | {p['price']:,.0f}đ | {p['status']} | {p['category']}")

    return "\n".join(lines) if lines else "❌ Không có dữ liệu."


def format_fallback(merged: dict) -> str:
    parts = [_fmt_one(r) for r in merged.get("all_results", []) if r.get("has_data")]
    return "\n\n".join(parts) if parts else "❌ Không có dữ liệu để trả lời."


# ══════════════════════════════════════════════════════════════
# LLM SYNTHESIZER
# ══════════════════════════════════════════════════════════════
async def synthesize(
    question:  str,
    merged:    dict,
    history:   list[dict],
) -> str:
    """
    Gọi Ollama với data thực. temperature=0.05 để giảm hallucination.
    """
    # Build data block — chỉ lấy phần có data
    data_blocks: list[str] = []
    for r in merged.get("all_results", []):
        if r.get("has_data"):
            label = r["intent"]
            chunk = json.dumps(r["data"], ensure_ascii=False, indent=2, default=str)
            data_blocks.append(f"### {label}\n{chunk}")

    data_str = "\n\n".join(data_blocks) if data_blocks else "(trống)"

    # Build history block
    hist_lines: list[str] = []
    for h in history[-6:]:
        role = "Người dùng" if h["role"] == "user" else "Trợ lý"
        hist_lines.append(f"  {role}: {h['content']}")
    hist_str = "\n".join(hist_lines)

    parts = [_SYSTEM]
    if hist_str:
        parts.append(f"[LỊCH SỬ]\n{hist_str}")
    if merged.get("has_data"):
        parts.append(
            f"[DATA — chỉ được dùng các giá trị trong này, không tự thêm]\n{data_str}"
        )
    parts.append(f"[CÂU HỎI]\n{question}")
    parts.append("[TRẢ LỜI]")

    prompt = "\n\n".join(parts)

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as c:
            res = await c.post(
                OLLAMA_URL,
                json={
                    "model":   OLLAMA_MODEL,
                    "prompt":  prompt,
                    "stream":  False,
                    "options": {"temperature": 0.05},
                },
            )
            if res.status_code == 200:
                return res.json().get("response", "").strip()
    except httpx.ConnectError:
        pass
    except Exception as e:
        logger.warning(f"LLM error: {e}")

    # LLM không khả dụng → fallback formatter
    return format_fallback(merged)
