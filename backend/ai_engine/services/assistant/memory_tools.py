"""
Cong cu CRUD cho Session Persistent Memory (them / sua / xoa cac truong cot loi trong phien).
Tat ca thao tac duoc kiem dinh chat bang Pydantic theo allowlist, gioi han dung luong
va co lap tuyet doi theo (user_id, session_id).
"""

import json
import re
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ValidationError

from .session_store import DomainKey, get_domain_context, save_persistent_memory

MAX_USER_PREFERENCES = 8
MAX_PINNED_FACTS = 10
MAX_SCALAR_CHARS = 100
MAX_PREF_VALUE_CHARS = 120
MAX_FACT_VALUE_CHARS = 180

MemoryAction = Literal["set", "add", "update", "delete"]
MemoryField = Literal[
    "active_period",
    "last_dashboard_period",
    "active_artist",
    "active_genre",
    "active_track",
    "user_preferences",
    "pinned_facts",
]

SCALAR_TEXT_FIELDS = {"active_artist", "active_genre", "active_track"}
PERIOD_DICT_FIELDS = {"active_period", "last_dashboard_period"}
MAP_FIELDS = {"user_preferences", "pinned_facts"}

_MEMORY_OPS_CLOSED_REGEX = re.compile(r"<memory_ops>\s*([\s\S]*?)\s*</memory_ops>", flags=re.IGNORECASE)
_MEMORY_OPS_UNCLOSED_REGEX = re.compile(r"<memory_ops>[\s\S]*$", flags=re.IGNORECASE)
_TAG_CLEAN_REGEX = re.compile(r"</?[a-zA-Z0-9_]+>")


class MemoryOperation(BaseModel):
    """Cau truc 1 thao tac them / sua / xoa tren Session Persistent Memory."""

    action: MemoryAction
    field: MemoryField
    key: str | None = None
    value: Any = None


def _sanitize_text(raw: Any, max_len: int) -> str:
    text = _TAG_CLEAN_REGEX.sub("", str(raw or "")).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:max_len]


def _sanitize_key(raw: str | None, fallback_prefix: str = "item") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", str(raw or "").strip().lower()).strip("_")
    return cleaned[:40] or fallback_prefix


def _validate_period_payload(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    s_str = str(raw.get("start_date") or "").strip()
    e_str = str(raw.get("end_date") or "").strip()
    if not s_str or not e_str:
        return None
    try:
        s_d = datetime.strptime(s_str, "%Y-%m-%d").date()
        e_d = datetime.strptime(e_str, "%Y-%m-%d").date()
        if s_d > e_d or (e_d - s_d).days > 731:
            return None
    except ValueError:
        return None

    result = {
        "start_date": s_d.isoformat(),
        "end_date": e_d.isoformat(),
    }
    if raw.get("label"):
        result["label"] = _sanitize_text(raw["label"], 80)
    if raw.get("period_type") in ("week", "month", "year"):
        result["period_type"] = raw["period_type"]
    if raw.get("source") in ("dashboard_period", "requested_in_query", "rolling_window"):
        result["source"] = raw["source"]
    return result


def extract_and_strip_memory_ops(raw_text: str) -> tuple[str, list[dict]]:
    """
    Tach khoi <memory_ops>[...]</memory_ops> tu phan hoi LLM va xoa sach khoi van ban hien thi.
    """
    if not raw_text:
        return "", []

    ops: list[dict] = []
    matches = _MEMORY_OPS_CLOSED_REGEX.findall(raw_text)
    for raw_json in matches:
        try:
            parsed = json.loads(raw_json)
            if isinstance(parsed, list):
                ops.extend(item for item in parsed if isinstance(item, dict))
            elif isinstance(parsed, dict):
                ops.append(parsed)
        except (ValueError, TypeError):
            continue

    cleaned = _MEMORY_OPS_CLOSED_REGEX.sub("", raw_text)
    cleaned = _MEMORY_OPS_UNCLOSED_REGEX.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, ops


def tool_update_session_memory(
    user_id: int,
    session_id: str | None,
    domain: DomainKey,
    operations: list[dict | MemoryOperation],
) -> dict:
    """
    Tool CRUD cho phep Agent/he thong them, sua, xoa cac truong trong Session Persistent Memory.
    Tra ve so thao tac da ap dung va snapshot bo nho moi nhat.
    """
    if not operations:
        ctx = get_domain_context(user_id, session_id, domain)
        return {
            "applied": 0,
            "skipped": 0,
            "operations_summary": [],
            "persistent_memory": ctx["persistent_memory"],
        }

    ctx = get_domain_context(user_id, session_id, domain)
    pm = dict(ctx["persistent_memory"])
    pm["user_preferences"] = dict(pm.get("user_preferences") or {})
    pm["pinned_facts"] = dict(pm.get("pinned_facts") or {})

    applied = 0
    skipped = 0
    summary_log: list[str] = []

    for raw_op in operations[:15]:
        try:
            op = raw_op if isinstance(raw_op, MemoryOperation) else MemoryOperation.model_validate(raw_op)
        except ValidationError:
            skipped += 1
            continue

        field = op.field
        action = op.action

        if field in SCALAR_TEXT_FIELDS:
            if action == "delete":
                if pm.get(field) is not None:
                    pm[field] = None
                    applied += 1
                    summary_log.append(f"delete:{field}")
                else:
                    skipped += 1
            else:
                val = _sanitize_text(op.value, MAX_SCALAR_CHARS)
                if not val:
                    skipped += 1
                    continue
                pm[field] = val
                applied += 1
                summary_log.append(f"{action}:{field}")
            continue

        if field in PERIOD_DICT_FIELDS:
            if action == "delete":
                pm[field] = None
                applied += 1
                summary_log.append(f"delete:{field}")
            else:
                valid_period = _validate_period_payload(op.value)
                if not valid_period:
                    skipped += 1
                    continue
                pm[field] = valid_period
                applied += 1
                summary_log.append(f"{action}:{field}")
            continue

        if field in MAP_FIELDS:
            target_map = pm[field]
            max_items = MAX_USER_PREFERENCES if field == "user_preferences" else MAX_PINNED_FACTS
            max_val_len = MAX_PREF_VALUE_CHARS if field == "user_preferences" else MAX_FACT_VALUE_CHARS

            if action == "delete":
                if op.key == "*":
                    target_map.clear()
                    applied += 1
                    summary_log.append(f"delete:{field}:*")
                elif op.key:
                    norm_k = _sanitize_key(op.key)
                    if norm_k in target_map:
                        del target_map[norm_k]
                        applied += 1
                        summary_log.append(f"delete:{field}:{norm_k}")
                    elif op.key in target_map:
                        del target_map[op.key]
                        applied += 1
                        summary_log.append(f"delete:{field}:{op.key}")
                    else:
                        skipped += 1
                else:
                    skipped += 1
            else:
                val = _sanitize_text(op.value, max_val_len)
                if not val:
                    skipped += 1
                    continue
                k = _sanitize_key(op.key, fallback_prefix=f"note_{len(target_map) + 1}")
                if k not in target_map and len(target_map) >= max_items:
                    oldest_key = next(iter(target_map))
                    del target_map[oldest_key]
                target_map[k] = val
                applied += 1
                summary_log.append(f"{action}:{field}:{k}")

    saved_pm = save_persistent_memory(user_id, session_id, domain, pm) if applied > 0 else pm
    return {
        "applied": applied,
        "skipped": skipped,
        "operations_summary": summary_log,
        "persistent_memory": saved_pm,
    }
