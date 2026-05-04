"""
chatbot.py — Router (thin layer, chỉ orchestrate các service)
Architecture: Intent → Cache → Repo → RAG → LLM
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.database import get_db
from app.chatbot.intent.classifier import parse_query
from app.chatbot.service import execute_multi_intent, pre_validate, synthesize
from app.chatbot.utils import build_history_ctx

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


# ── Schemas ───────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role:    str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


# ── Endpoint ──────────────────────────────────────────────────
@router.post("/")
async def chat(
    req:          ChatRequest,
    current_user  = Depends(get_current_user),
    db: Session   = Depends(get_db),
):
    message = req.message.strip()
    if not message:
        return {"reply": "Vui lòng nhập câu hỏi.", "intents": [], "sources": []}

    history = [h.model_dump() for h in req.history]

    # 1. Parse query → intents + date range
    history_ctx = build_history_ctx(history)
    pq = await parse_query(message, history_ctx)

    # 2. Execute (cache → DB) cho tất cả intent
    merged = execute_multi_intent(pq, db)

    # 3. Pre-validate — trả lời sớm nếu không có data
    early = pre_validate(merged)
    if early:
        return {
            "reply":       early,
            "intents":     merged.get("intents", []),
            "sources":     ["database"],
            "has_db_data": False,
        }

    # 4. LLM synthesize (hoặc fallback formatter)
    answer = await synthesize(message, merged, history)

    return {
        "reply":       answer,
        "intents":     merged.get("intents", []),
        "sources":     ["database"] if merged.get("has_data") else ["rule-based"],
        "has_db_data": merged.get("has_data", False),
        "period":      merged.get("period_label", ""),
    }


# ── RAG index rebuild endpoint (gọi sau khi thêm sản phẩm) ───
@router.post("/rebuild-index")
def rebuild_rag_index(
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    """Rebuild FAISS semantic index. Gọi sau khi import sản phẩm lớn."""
    from app.models.product import Product
    from app.models.category import Category
    from app.chatbot.rag import rebuild_index

    product_names  = [p.name for p in db.query(Product).all()]
    category_names = [c.name for c in db.query(Category).all()]
    rebuild_index(product_names, category_names)

    return {"message": f"Rebuilt index: {len(product_names)} SP, {len(category_names)} DM"}
