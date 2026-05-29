from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

import httpx

from . import Intent, INTENT_DESCRIPTIONS, KEYWORD_MAP, ParsedQuery

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"


# ──────────────────────────────────────────────────────────────────
# DATE PARSER
# ──────────────────────────────────────────────────────────────────
def parse_date_range(msg: str) -> tuple[Optional[date], Optional[date], str]:
    s = msg.lower()
    today = date.today()

    if "hôm nay" in s or "today" in s:
        return today, today, f"ngày {today.strftime('%d/%m/%Y')}"
    if "hôm qua" in s or "yesterday" in s:
        d = today - timedelta(days=1)
        return d, d, f"ngày {d.strftime('%d/%m/%Y')}"
    if "tuần này" in s or "this week" in s:
        start = today - timedelta(days=today.weekday())
        return start, today, "tuần này"
    if "tuần trước" in s or "last week" in s:
        start = today - timedelta(days=today.weekday() + 7)
        end   = start + timedelta(days=6)
        return start, end, "tuần trước"
    if "tháng này" in s or "this month" in s:
        return today.replace(day=1), today, "tháng này"
    if "tháng trước" in s or "last month" in s:
        first = today.replace(day=1)
        last  = first - timedelta(days=1)
        return last.replace(day=1), last, "tháng trước"
    if "7 ngày" in s or "một tuần" in s:
        return today - timedelta(days=7), today, "7 ngày gần nhất"
    if "30 ngày" in s or "một tháng" in s:
        return today - timedelta(days=30), today, "30 ngày gần nhất"

    # "ngày 20 tháng 4 năm 2025" / "20/4/2025" / "20/4"
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{4}))?", s)
    if not m:
        m = re.search(
            r"ngày\s+(\d{1,2})[,\s]+tháng\s+(\d{1,2})(?:[,\s]+năm\s+(\d{4}))?", s
        )
    if m:
        try:
            day   = int(m.group(1))
            month = int(m.group(2))
            year  = int(m.group(3)) if m.group(3) else today.year
            d = date(year, month, day)
            return d, d, f"ngày {d.strftime('%d/%m/%Y')}"
        except (ValueError, IndexError):
            pass

    # "ngày 20" → ngày 20 tháng hiện tại
    m_day = re.search(r"(?<!\d)ngày\s+(\d{1,2})(?!\s*tháng|\s*\d)", s)
    if m_day:
        try:
            d = today.replace(day=int(m_day.group(1)))
            return d, d, f"ngày {d.strftime('%d/%m/%Y')}"
        except ValueError:
            pass

    # "tháng 4" / "tháng 4 năm 2024"
    m_month = re.search(r"tháng\s+(\d{1,2})(?:\s+năm\s+(\d{4}))?", s)
    if m_month:
        month = int(m_month.group(1))
        year  = int(m_month.group(2)) if m_month.group(2) else today.year
        try:
            start = date(year, month, 1)
            end   = (date(year, month + 1, 1) - timedelta(days=1)
                     if month < 12 else date(year, 12, 31))
            return start, end, f"tháng {month:02d}/{year}"
        except ValueError:
            pass

    return None, None, "tất cả thời gian"


# ──────────────────────────────────────────────────────────────────
# MULTI-INTENT CLASSIFIER
# ──────────────────────────────────────────────────────────────────
def classify_multi_intent_fast(message: str) -> list[Intent]:
    msg = message.lower()
    found: list[Intent] = []
    for keywords, intent in KEYWORD_MAP:
        if any(k in msg for k in keywords):
            if intent not in found:
                found.append(intent)
    return found


async def classify_multi_intent_llm(message: str, history_ctx: str) -> list[Intent]:
    labels_str = "\n".join(
        [f"  {i.value}: {d}" for i, d in INTENT_DESCRIPTIONS.items()]
    )
    prompt = (
        "Bạn là intent classifier. Phân loại câu hỏi thành MỘT HOẶC NHIỀU nhãn.\n\n"
        f"Nhãn có thể dùng:\n{labels_str}\n\n"
        + (f"Lịch sử gần nhất:\n{history_ctx}\n\n" if history_ctx else "")
        + f"Câu hỏi: \"{message}\"\n\n"
        "Trả lời chỉ tên nhãn, nếu nhiều nhãn thì ngăn cách bằng dấu phẩy.\n"
        "Ví dụ: DB_REVENUE,DB_TOP_PRODUCTS"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            res = await c.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
            )
            if res.status_code == 200:
                raw = res.json().get("response", "").strip().upper()
                intents: list[Intent] = []
                for token in re.split(r"[,\s]+", raw):
                    token = token.strip()
                    try:
                        intents.append(Intent(token))
                    except ValueError:
                        pass
                if intents:
                    return intents
    except Exception:
        pass
    return [Intent.GENERAL]


async def parse_query(message: str, history_ctx: str = "") -> ParsedQuery:
    sd, ed, label = parse_date_range(message)

    intents = classify_multi_intent_fast(message)

    if not intents:
        intents = await classify_multi_intent_llm(message, history_ctx)

    return ParsedQuery(
        intents=intents,
        start_date=sd,
        end_date=ed,
        raw_message=message,
        period_label=label,
    )
