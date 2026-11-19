"""
Quan ly bo nho 2 lop theo phien (Session-Scoped & User-Isolated):
1) Session Persistent Memory: luu cau hinh/trang thai cot loi xuyen suot phien
   (active_period, active_artist, active_genre, active_track, user_preferences, pinned_facts).
2) Session Episodic Memory: giu 6 luot chi tiet gan nhat va tu dong nen cac luot cu hon.
"""

import re
import time
from typing import Literal
from django.core.cache import cache

SESSION_TTL_SECONDS = 1800
MAX_TURNS_PER_DOMAIN = 6
MAX_SUMMARY_CHARS = 420
MAX_MEMORY_CHARS = 1200

DomainKey = Literal["music_insights", "website_support"]


def _default_persistent_memory() -> dict:
    return {
        "active_period": None,
        "last_dashboard_period": None,
        "active_artist": None,
        "active_genre": None,
        "active_track": None,
        "user_preferences": {},
        "pinned_facts": {},
    }


def _normalize_persistent_memory(raw: dict | None) -> dict:
    base = _default_persistent_memory()
    if not isinstance(raw, dict):
        return base
    if isinstance(raw.get("active_period"), dict):
        base["active_period"] = dict(raw["active_period"])
    if isinstance(raw.get("last_dashboard_period"), dict):
        base["last_dashboard_period"] = dict(raw["last_dashboard_period"])
    for scalar_key in ("active_artist", "active_genre", "active_track"):
        val = raw.get(scalar_key)
        base[scalar_key] = str(val).strip() if isinstance(val, str) and val.strip() else None
    if isinstance(raw.get("user_preferences"), dict):
        base["user_preferences"] = {
            str(k): str(v) for k, v in raw["user_preferences"].items() if k and v is not None
        }
    if isinstance(raw.get("pinned_facts"), dict):
        base["pinned_facts"] = {
            str(k): str(v) for k, v in raw["pinned_facts"].items() if k and v is not None
        }
    return base


def _sync_entities_from_persistent(pm: dict, existing_entities: dict | None = None) -> dict:
    """Dong bo music_entities tu persistent_memory de dam bao tuong thich nguoc."""
    entities = dict(existing_entities or {})
    if pm.get("active_artist"):
        entities["last_artist"] = pm["active_artist"]
    else:
        entities.pop("last_artist", None)
    if pm.get("active_genre"):
        entities["last_genre"] = pm["active_genre"]
    else:
        entities.pop("last_genre", None)
    if pm.get("active_track"):
        entities["last_track"] = pm["active_track"]
    else:
        entities.pop("last_track", None)
    if pm.get("active_period"):
        entities["last_period"] = dict(pm["active_period"])
    else:
        entities.pop("last_period", None)
    if pm.get("last_dashboard_period"):
        entities["last_dashboard_period"] = dict(pm["last_dashboard_period"])
    else:
        entities.pop("last_dashboard_period", None)
    return entities


def render_persistent_memory_markdown(pm: dict | None) -> str:
    """Xuat Session Persistent Memory thanh khoi ghi nho gon gang kieu MEMORY.md cho LLM."""
    norm = _normalize_persistent_memory(pm)
    lines: list[str] = []

    ap = norm.get("active_period")
    if isinstance(ap, dict) and ap.get("start_date") and ap.get("end_date"):
        lines.append(
            f"- Pham vi thoi gian dang lam viec: {ap.get('label') or ''} "
            f"({ap['start_date']} den {ap['end_date']}, nguon: {ap.get('source', 'unknown')})"
        )
    if norm.get("active_artist"):
        lines.append(f"- Nghe si dang thao luan: {norm['active_artist']}")
    if norm.get("active_genre"):
        lines.append(f"- The loai dang thao luan: {norm['active_genre']}")
    if norm.get("active_track"):
        lines.append(f"- Bai hat dang thao luan: {norm['active_track']}")

    prefs = norm.get("user_preferences") or {}
    if prefs:
        lines.append("- Tuy chon nguoi dung trong phien:")
        for k, v in prefs.items():
            lines.append(f"  - {k}: {v}")

    facts = norm.get("pinned_facts") or {}
    if facts:
        lines.append("- Cac moc so lieu da ghim trong phien:")
        for k, v in facts.items():
            lines.append(f"  - [{k}] {v}")

    return "\n".join(lines)


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


def _format_evicted_turn_line(turn: dict) -> str:
    scope = str(turn.get("scope_label") or "").strip()
    query = _condense_text(str(turn.get("query") or ""), 90)
    answer = _condense_text(str(turn.get("answer_summary") or ""), 150)
    entities = turn.get("entities") if isinstance(turn.get("entities"), dict) else {}
    entity_tags: list[str] = []
    if entities.get("last_artist"):
        entity_tags.append(f"nghệ sĩ: {entities['last_artist']}")
    if entities.get("last_genre"):
        entity_tags.append(f"thể loại: {entities['last_genre']}")
    if entities.get("last_track"):
        entity_tags.append(f"bài hát: {entities['last_track']}")
    prefix = f"[{scope}] " if scope else ""
    tag_suffix = f" ({'; '.join(entity_tags)})" if entity_tags else ""
    return f"- {prefix}Hỏi: {query} -> {answer}{tag_suffix}"


def _merge_evicted_turns_into_memory(existing_memory: str, evicted_turns: list[dict]) -> str:
    """Nen cac luot bi day ra khoi cua so 6 luot vao bo nho tich luy gioi han ky tu."""
    lines = [ln.strip() for ln in (existing_memory or "").splitlines() if ln.strip()]
    for turn in evicted_turns:
        lines.append(_format_evicted_turn_line(turn))

    while len(lines) > 1 and len("\n".join(lines)) > MAX_MEMORY_CHARS:
        lines.pop(0)

    merged = "\n".join(lines)
    if len(merged) > MAX_MEMORY_CHARS:
        merged = merged[-MAX_MEMORY_CHARS:]
    return merged


def get_session_state(user_id: int, session_id: str | None) -> dict:
    """Doc trang thai hoi thoai 2 lop cua rieng user_id va session_id."""
    key = _build_cache_key(user_id, session_id)
    data = cache.get(key)
    if not isinstance(data, dict):
        return {
            "music_turns": [],
            "music_memory": "",
            "music_persistent_memory": _default_persistent_memory(),
            "music_entities": {},
            "music_total_turns": 0,
            "website_turns": [],
            "website_memory": "",
            "website_persistent_memory": _default_persistent_memory(),
            "website_total_turns": 0,
            "last_domain": None,
        }

    music_turns = list(data.get("music_turns") or [])
    website_turns = list(data.get("website_turns") or [])
    music_pm = _normalize_persistent_memory(data.get("music_persistent_memory"))
    website_pm = _normalize_persistent_memory(data.get("website_persistent_memory"))

    # Tuong thich du lieu cu neu cache chi co music_entities
    raw_entities = dict(data.get("music_entities") or {})
    if not music_pm.get("active_artist") and raw_entities.get("last_artist"):
        music_pm["active_artist"] = str(raw_entities["last_artist"])
    if not music_pm.get("active_genre") and raw_entities.get("last_genre"):
        music_pm["active_genre"] = str(raw_entities["last_genre"])
    if not music_pm.get("active_track") and raw_entities.get("last_track"):
        music_pm["active_track"] = str(raw_entities["last_track"])
    if not music_pm.get("active_period") and isinstance(raw_entities.get("last_period"), dict):
        music_pm["active_period"] = dict(raw_entities["last_period"])

    return {
        "music_turns": music_turns,
        "music_memory": str(data.get("music_memory") or ""),
        "music_persistent_memory": music_pm,
        "music_entities": _sync_entities_from_persistent(music_pm, raw_entities),
        "music_total_turns": int(data.get("music_total_turns") or len(music_turns)),
        "website_turns": website_turns,
        "website_memory": str(data.get("website_memory") or ""),
        "website_persistent_memory": website_pm,
        "website_total_turns": int(data.get("website_total_turns") or len(website_turns)),
        "last_domain": data.get("last_domain"),
    }


def save_persistent_memory(
    user_id: int,
    session_id: str | None,
    domain: DomainKey,
    persistent_memory: dict,
) -> dict:
    """Luu tru truc tiep Session Persistent Memory da validate cua user."""
    state = get_session_state(user_id, session_id)
    normalized = _normalize_persistent_memory(persistent_memory)
    if domain == "music_insights":
        state["music_persistent_memory"] = normalized
        state["music_entities"] = _sync_entities_from_persistent(
            normalized, state.get("music_entities")
        )
    else:
        state["website_persistent_memory"] = normalized
    cache.set(_build_cache_key(user_id, session_id), state, timeout=SESSION_TTL_SECONDS)
    return normalized


def get_domain_turns(user_id: int, session_id: str | None, domain: DomainKey) -> list[dict]:
    """Lay lich su gan nhat cua dung mot mien tri thuc (khong tron lan hai mien)."""
    state = get_session_state(user_id, session_id)
    field = "music_turns" if domain == "music_insights" else "website_turns"
    return list(state.get(field) or [])


def get_domain_context(user_id: int, session_id: str | None, domain: DomainKey) -> dict:
    """Lay day du bo nho 2 lop cua mien: persistent_memory + episodic turns & compressed_memory."""
    state = get_session_state(user_id, session_id)
    if domain == "music_insights":
        pm = state["music_persistent_memory"]
        memory = state["music_memory"]
        return {
            "turns": state["music_turns"],
            "compressed_memory": memory,
            "persistent_memory": pm,
            "persistent_memory_markdown": render_persistent_memory_markdown(pm),
            "entities": state["music_entities"],
            "total_turns": state["music_total_turns"],
            "has_compressed_memory": bool(memory.strip()),
        }
    pm = state["website_persistent_memory"]
    memory = state["website_memory"]
    return {
        "turns": state["website_turns"],
        "compressed_memory": memory,
        "persistent_memory": pm,
        "persistent_memory_markdown": render_persistent_memory_markdown(pm),
        "entities": {},
        "total_turns": state["website_total_turns"],
        "has_compressed_memory": bool(memory.strip()),
    }


def append_domain_turn(
    user_id: int,
    session_id: str | None,
    domain: DomainKey,
    user_query: str,
    answer_text: str,
    scope_label: str = "",
    entities: dict | None = None,
) -> dict:
    """
    Luu luot hoi-dap vao Episodic Memory cua user.
    Khi vuot qua 6 luot, tu dong nen cac luot cu nhat vao bo nho tich luy thay vi xoa bo.
    """
    state = get_session_state(user_id, session_id)
    is_music = domain == "music_insights"
    turns_field = "music_turns" if is_music else "website_turns"
    memory_field = "music_memory" if is_music else "website_memory"
    total_field = "music_total_turns" if is_music else "website_total_turns"

    turns = list(state.get(turns_field) or [])
    clean_entities: dict = {}
    if isinstance(entities, dict):
        for k in ("last_artist", "last_genre", "last_track", "last_period", "last_dashboard_period", "last_tools"):
            if entities.get(k):
                clean_entities[k] = entities[k]

    turns.append(
        {
            "query": _condense_text(user_query, 240),
            "answer_summary": _condense_text(answer_text, MAX_SUMMARY_CHARS),
            "scope_label": (scope_label or "")[:80],
            "entities": clean_entities,
            "ts": int(time.time()),
        }
    )

    if len(turns) > MAX_TURNS_PER_DOMAIN:
        evicted = turns[:-MAX_TURNS_PER_DOMAIN]
        state[memory_field] = _merge_evicted_turns_into_memory(
            state.get(memory_field, ""),
            evicted,
        )
        turns = turns[-MAX_TURNS_PER_DOMAIN:]

    state[turns_field] = turns
    state[total_field] = int(state.get(total_field) or 0) + 1
    if is_music and clean_entities:
        merged_entities = dict(state.get("music_entities") or {})
        merged_entities.update(clean_entities)
        state["music_entities"] = merged_entities

    state["last_domain"] = domain
    cache.set(_build_cache_key(user_id, session_id), state, timeout=SESSION_TTL_SECONDS)
    return {
        "total_turns": state[total_field],
        "has_compressed_memory": bool(str(state.get(memory_field) or "").strip()),
    }


def clear_session(user_id: int, session_id: str | None = None) -> None:
    """Xoa ngay ca Persistent Memory lan Episodic Memory trong phien cua user hien tai."""
    cache.delete(_build_cache_key(user_id, session_id))
