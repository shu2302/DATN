from __future__ import annotations


def build_history_ctx(history: list[dict], n: int = 6) -> str:
    lines = []
    for h in history[-n:]:
        role = "Người dùng" if h.get("role") == "user" else "Trợ lý"
        lines.append(f"{role}: {h.get('content', '')}")
    return "\n".join(lines)
