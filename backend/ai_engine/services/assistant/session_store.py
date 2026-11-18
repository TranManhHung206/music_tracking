"""
Quan ly ngu canh hoi thoai theo phien (Session-Scoped & User-Isolated).
Tach biet ranh gioi ngu canh giua Music Insights va Website Support.
"""

import re
import time
from typing import Literal
from django.core.cache import cache

SESSION_TTL_SECONDS = 1800
MAX_TURNS_PER_DOMAIN = 6
MAX_SUMMARY_CHARS = 420

DomainKey = Literal["music_insights", "website_support"]


def _sanitize_session_id(session_id: str | None) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", str(session_id or "default"))
    return cleaned[:64] or "default"


def _build_cache_key(user_id: int, session_id: str | None) -> str:
    safe_sid = _sanitize_session_id(session_id)
    return f"assistant_session:v1:{int(user_id)}:{safe_sid}"


def _condense_text(text: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3] + "..."


def get_session_state(user_id: int, session_id: str | None) -> dict:
    """Doc trang thai hoi thoai cua rieng user_id va session_id."""
    key = _build_cache_key(user_id, session_id)
    data = cache.get(key)
    if not isinstance(data, dict):
        return {
            "music_turns": [],
            "website_turns": [],
            "last_domain": None,
        }
    return {
        "music_turns": list(data.get("music_turns") or []),
        "website_turns": list(data.get("website_turns") or []),
        "last_domain": data.get("last_domain"),
    }


def get_domain_turns(user_id: int, session_id: str | None, domain: DomainKey) -> list[dict]:
    """Lay lich su gan nhat cua dung mot mien tri thuc (khong tron lan hai mien)."""
    state = get_session_state(user_id, session_id)
    field = "music_turns" if domain == "music_insights" else "website_turns"
    return list(state.get(field) or [])


def append_domain_turn(
    user_id: int,
    session_id: str | None,
    domain: DomainKey,
    user_query: str,
    answer_text: str,
    scope_label: str = "",
) -> int:
    """Luu luot hoi-dap da duoc rut gon an toan vao cache phien cua chinh user."""
    state = get_session_state(user_id, session_id)
    field = "music_turns" if domain == "music_insights" else "website_turns"
    turns = list(state.get(field) or [])
    turns.append({
        "query": _condense_text(user_query, 240),
        "answer_summary": _condense_text(answer_text, MAX_SUMMARY_CHARS),
        "scope_label": (scope_label or "")[:80],
        "ts": int(time.time()),
    })
    state[field] = turns[-MAX_TURNS_PER_DOMAIN:]
    state["last_domain"] = domain
    cache.set(_build_cache_key(user_id, session_id), state, timeout=SESSION_TTL_SECONDS)
    return len(state[field])


def clear_session(user_id: int, session_id: str | None = None) -> None:
    """Xoa ngay lich su hoi thoai trong phien cua user hien tai."""
    cache.delete(_build_cache_key(user_id, session_id))
