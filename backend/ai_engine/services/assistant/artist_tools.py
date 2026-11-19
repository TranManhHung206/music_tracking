"""
Bo cong cu chuyen biet tong hop du lieu cho 1 nghe si cu the trong 1 khoang thoi gian.
Moi sub-tool nhan input tuong minh (user, artist_name, start_date, end_date),
chi doc (Read-Only) va co lap tuyet doi theo tai khoan user dang dang nhap.
"""

import calendar
import json
import logging
import os
import re
from datetime import date, datetime, time, timedelta
from django.conf import settings
from django.db.models import Count, Max, Min, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from pydantic import BaseModel

from ai_engine.services.llm_client import (
    OpenAICompatibleClient,
    get_ai_provider_order,
    get_openai_compatible_config,
    strip_reasoning_blocks,
)
from tracker.models import Artist, ListeningHistory
from .intent_router import normalize_vi_text
from .schemas import AssistantEvidenceItem

logger = logging.getLogger(__name__)

ARTIST_COREF_PHRASES = (
    "nghe si do",
    "ca si do",
    "nghe si nay",
    "ca si nay",
    "nghe si ay",
    "ca si ay",
    "ban nhac do",
    "cua ho",
    "ve ho",
    "cua anh ay",
    "ve anh ay",
    "cua co ay",
    "ve co ay",
    "nguoi do",
    "nghe ho",
)

GENERIC_NON_ARTIST_TOKENS = {
    "nao",
    "gi",
    "ai",
    "toi",
    "minh",
    "tui",
    "ban",
    "ho",
    "nhieu nhat",
    "top",
    "tuan nay",
    "tuan truoc",
    "thang nay",
    "thang truoc",
    "nam nay",
    "nam truoc",
    "nam ngoai",
    "ky nay",
    "ky truoc",
    "he thong",
    "website",
    "musictrack",
    "spotify",
    "nghe si",
    "ca si",
    "bai hat",
    "album",
    "the loai",
}


class ExtractedArtistParams(BaseModel):
    """Schema validate ket qua trich xuat tham so tu LLM tang 2."""

    artist_name: str | None = None
    start_date: str | None = None
    end_date: str | None = None


def _format_duration_vi(total_duration_ms: int) -> str:
    if total_duration_ms <= 0:
        return "0 phút"
    total_minutes = round(total_duration_ms / 60000)
    if total_minutes < 60:
        return f"{max(total_minutes, 1)} phút"
    hours_val = round(total_duration_ms / 3600000, 2)
    return f"{hours_val} giờ"


def _parse_iso_date(raw: str | None) -> date | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _date_bounds_aware(start_d: date, end_d: date) -> tuple[datetime, datetime]:
    user_tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_d, time.min), user_tz)
    end_dt = timezone.make_aware(datetime.combine(end_d, time.max), user_tz)
    return start_dt, end_dt


def _infer_period_type(start_d: date, end_d: date) -> str:
    span = (end_d - start_d).days
    if span <= 8:
        return "week"
    if span <= 35:
        return "month"
    return "year"


def extract_date_range_from_text(query_text: str) -> tuple[date, date, str, str] | None:
    """
    Trich xuat khoang thoi gian tu cau hoi tieng Viet:
    ho tro khoang ngay tuong minh, thang/quy/nam cu the va cac moc tuong doi.
    """
    norm = normalize_vi_text(query_text)
    today = timezone.localdate()

    # 1. Khoang ISO: tu 2026-10-01 den 2026-10-31
    iso_range = re.search(
        r"(\d{4}-\d{2}-\d{2})\s*(?:den|toi|-|~)\s*(\d{4}-\d{2}-\d{2})",
        norm,
    )
    if iso_range:
        s_d = _parse_iso_date(iso_range.group(1))
        e_d = _parse_iso_date(iso_range.group(2))
        if s_d and e_d and s_d <= e_d and (e_d - s_d).days <= 731:
            return (
                s_d,
                e_d,
                _infer_period_type(s_d, e_d),
                f"{s_d.strftime('%d/%m/%Y')} - {e_d.strftime('%d/%m/%Y')}",
            )

    # 2. Khoang dd/mm(/yyyy) den dd/mm(/yyyy)
    dmy_range = re.search(
        r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\s*(?:den|toi|-|~)\s*(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?",
        norm,
    )
    if dmy_range:
        try:
            d1, m1 = int(dmy_range.group(1)), int(dmy_range.group(2))
            d2, m2 = int(dmy_range.group(4)), int(dmy_range.group(5))
            y2 = int(dmy_range.group(6)) if dmy_range.group(6) else today.year
            y1 = int(dmy_range.group(3)) if dmy_range.group(3) else y2
            s_d = date(y1, m1, d1)
            e_d = date(y2, m2, d2)
            if s_d <= e_d and (e_d - s_d).days <= 731:
                return (
                    s_d,
                    e_d,
                    _infer_period_type(s_d, e_d),
                    f"{s_d.strftime('%d/%m/%Y')} - {e_d.strftime('%d/%m/%Y')}",
                )
        except ValueError:
            pass

    # 3. Khoang tu thang M(/YYYY) den thang N(/YYYY)
    month_range = re.search(
        r"tu\s+thang\s+(\d{1,2})(?:\s*(?:/|nam)\s*(\d{4}))?\s*(?:den|toi)\s*thang\s+(\d{1,2})(?:\s*(?:/|nam)\s*(\d{4}))?",
        norm,
    )
    if month_range:
        try:
            m1, m2 = int(month_range.group(1)), int(month_range.group(3))
            y2 = int(month_range.group(4)) if month_range.group(4) else today.year
            y1 = int(month_range.group(2)) if month_range.group(2) else y2
            if 1 <= m1 <= 12 and 1 <= m2 <= 12:
                s_d = date(y1, m1, 1)
                e_d = date(y2, m2, calendar.monthrange(y2, m2)[1])
                if s_d <= e_d and (e_d - s_d).days <= 731:
                    return (
                        s_d,
                        e_d,
                        _infer_period_type(s_d, e_d),
                        f"Tháng {m1:02d}/{y1} - Tháng {m2:02d}/{y2}",
                    )
        except ValueError:
            pass

    # 4. Quy cu the: quy 1..4 (nam YYYY)
    quarter_match = re.search(r"\bquy\s+([1-4])(?:\s*(?:/|nam)\s*(\d{4}))?\b", norm)
    if quarter_match:
        q_num = int(quarter_match.group(1))
        y_val = int(quarter_match.group(2)) if quarter_match.group(2) else today.year
        start_m = (q_num - 1) * 3 + 1
        end_m = start_m + 2
        s_d = date(y_val, start_m, 1)
        e_d = date(y_val, end_m, calendar.monthrange(y_val, end_m)[1])
        return s_d, e_d, "year", f"Quý {q_num}/{y_val}"

    # 5. Moc tuong doi pho bien
    if "hom qua" in norm:
        yd = today - timedelta(days=1)
        return yd, yd, "week", f"Hôm qua ({yd.strftime('%d/%m/%Y')})"

    if "hom nay" in norm:
        return today, today, "week", f"Hôm nay ({today.strftime('%d/%m/%Y')})"

    if "tuan truoc" in norm or "tuan qua" in norm:
        curr_mon = today - timedelta(days=today.weekday())
        prev_mon = curr_mon - timedelta(days=7)
        prev_sun = prev_mon + timedelta(days=6)
        iso_year, iso_week, _ = prev_mon.isocalendar()
        return prev_mon, prev_sun, "week", f"Tuần {iso_week} ({iso_year})"

    if "tuan nay" in norm:
        curr_mon = today - timedelta(days=today.weekday())
        curr_sun = curr_mon + timedelta(days=6)
        return curr_mon, curr_sun, "week", "Tuần này"

    if "thang truoc" in norm:
        prev_y, prev_m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        last_day = calendar.monthrange(prev_y, prev_m)[1]
        return date(prev_y, prev_m, 1), date(prev_y, prev_m, last_day), "month", f"Tháng {prev_m:02d}/{prev_y}"

    if "thang nay" in norm:
        last_day = calendar.monthrange(today.year, today.month)[1]
        return date(today.year, today.month, 1), date(today.year, today.month, last_day), "month", f"Tháng {today.month:02d}/{today.year}"

    # 6. Thang cu the: thang 10/2026, thang 10 nam 2026, thang 10
    month_match = re.search(r"\bthang\s+(1[0-2]|0?[1-9])(?:\s*(?:/|nam)\s*(\d{4}))?\b", norm)
    if month_match:
        m_val = int(month_match.group(1))
        y_val = int(month_match.group(2)) if month_match.group(2) else today.year
        last_day = calendar.monthrange(y_val, m_val)[1]
        return date(y_val, m_val, 1), date(y_val, m_val, last_day), "month", f"Tháng {m_val:02d}/{y_val}"

    if "nam truoc" in norm or "nam ngoai" in norm:
        py = today.year - 1
        return date(py, 1, 1), date(py, 12, 31), "year", f"Năm {py}"

    if "nam nay" in norm:
        return date(today.year, 1, 1), date(today.year, 12, 31), "year", f"Năm {today.year}"

    year_match = re.search(r"\bnam\s+(20\d{2})\b", norm)
    if year_match:
        y_val = int(year_match.group(1))
        return date(y_val, 1, 1), date(y_val, 12, 31), "year", f"Năm {y_val}"

    if "7 ngay" in norm:
        return today - timedelta(days=6), today, "week", "7 ngày gần nhất"

    if "30 ngay" in norm:
        return today - timedelta(days=29), today, "month", "30 ngày gần nhất"

    return None


def _get_user_listened_artists(user) -> list[Artist]:
    """Chi lay danh sach nghe si nam trong lich su nghe cua chinh user hien tai."""
    return list(
        Artist.objects.filter(tracks__play_records__user=user)
        .distinct()
        .only("id", "spotify_id", "name")[:500]
    )


def _match_artist_in_text(norm_q: str, user_artists: list[Artist]) -> Artist | None:
    """Khop ten nghe si cua user trong cau hoi, uu tien ten dai nhat va kiem tra bien tu."""
    candidates: list[tuple[str, Artist]] = []
    for art in user_artists:
        norm_name = normalize_vi_text(art.name)
        if len(norm_name) >= 2:
            candidates.append((norm_name, art))

    candidates.sort(key=lambda item: len(item[0]), reverse=True)
    for norm_name, art in candidates:
        pattern = r"(?<![a-z0-9])" + re.escape(norm_name) + r"(?![a-z0-9])"
        if re.search(pattern, norm_q):
            return art
    return None


def _extract_explicit_unknown_artist_name(query_text: str) -> str | None:
    """Nhan dien truong hop nguoi dung neu ro ten 1 nghe si khong co trong lich su cua ho."""
    patterns = (
        r"(?:nghe\s+si|nghệ\s+sĩ|ca\s+si|ca\s+sĩ)\s+[\"']?([A-Za-zÀ-ỹ0-9][A-Za-zÀ-ỹ0-9\s.&'-]{1,40})[\"']?",
    )
    stop_tail = re.compile(
        r"\s+(?:trong|tu|từ|thang|tháng|tuan|tuần|nam|năm|ky|kỳ|bao|nhieu|nhiều|may|mấy|nao|nào|co|có|la|là|ra|sao|khong|không)\b.*$",
        flags=re.IGNORECASE,
    )
    for pat in patterns:
        m = re.search(pat, query_text or "", flags=re.IGNORECASE)
        if not m:
            continue
        candidate = stop_tail.sub("", m.group(1)).strip(" ?.,!\"'")
        norm_cand = normalize_vi_text(candidate)
        if (
            len(norm_cand) >= 2
            and norm_cand not in GENERIC_NON_ARTIST_TOKENS
            and not any(norm_cand.startswith(prefix) for prefix in ("nao", "do", "nay", "ay", "nhieu"))
        ):
            return candidate
    return None


def try_extract_artist_params_with_llm(query_text: str, today_iso: str) -> ExtractedArtistParams | None:
    """
    Tang 2 tuy chon: chi dung khi cau hoi phuc tap nhung tang 1 chua tach duoc
    ten nghe si hoac khoang ngay. Validate chat bang Pydantic, fallback an toan.
    """
    system_prompt = (
        "Trích xuất JSON gồm 3 khóa: artist_name (string hoặc null), "
        "start_date (YYYY-MM-DD hoặc null), end_date (YYYY-MM-DD hoặc null). "
        f"Ngày hiện tại là {today_iso}. Chỉ trả về JSON hợp lệ, không giải thích."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query_text},
    ]

    raw_text = None
    for provider_key in get_ai_provider_order():
        try:
            if provider_key == "openai_compatible":
                cfg = get_openai_compatible_config()
                if not cfg.is_configured:
                    continue
                client = OpenAICompatibleClient(cfg)
                res = client.chat.completions.create(
                    model=cfg.model_candidates[0],
                    messages=messages,
                    temperature=0.0,
                    max_tokens=120,
                )
                raw_text = strip_reasoning_blocks(res.choices[0].message.content or "")
                if raw_text:
                    break
            elif provider_key == "groq":
                groq_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
                if not groq_key:
                    continue
                from groq import Groq
                client = Groq(api_key=groq_key)
                res = client.chat.completions.create(
                    model=getattr(settings, "AI_MODEL_GROQ_BACKUP", "llama-3.1-8b-instant"),
                    messages=messages,
                    temperature=0.0,
                    max_tokens=120,
                )
                raw_text = strip_reasoning_blocks(res.choices[0].message.content or "")
                if raw_text:
                    break
        except Exception as exc:
            logger.debug("Bo trich xuat tham so tang 2 (%s) bo qua: %s", provider_key, exc)

    if not raw_text:
        return None

    json_match = re.search(r"\{[\s\S]*\}", raw_text)
    if not json_match:
        return None

    try:
        parsed = json.loads(json_match.group(0))
        validated = ExtractedArtistParams.model_validate(parsed)
        if validated.start_date and not _parse_iso_date(validated.start_date):
            validated.start_date = None
        if validated.end_date and not _parse_iso_date(validated.end_date):
            validated.end_date = None
        return validated
    except Exception:
        return None


def extract_artist_target(
    user,
    query_text: str,
    session_entities: dict | None = None,
) -> tuple[str | None, str]:
    """
    Xac dinh ten nghe si muc tieu tu cau hoi hoac dai tu tham chieu trong bo nho phien.
    Tra ve (artist_name, source) voi source thuoc: 'matched_in_query' | 'session_coref' | 'explicit_unheard' | 'none'.
    """
    norm_q = normalize_vi_text(query_text)
    user_artists = _get_user_listened_artists(user)

    # 1. Khop truc tiep ten nghe si trong lich su nghe cua user
    matched = _match_artist_in_text(norm_q, user_artists)
    if matched:
        return matched.name, "matched_in_query"

    # 2. Giai tham chieu dai tu tu bo nho phien ("nghe si do", "ca si nay", "cua ho"...)
    last_artist = (session_entities or {}).get("last_artist")
    if last_artist and any(cue in norm_q for cue in ARTIST_COREF_PHRASES):
        return str(last_artist), "session_coref"

    # 3. Nguoi dung neu ro "nghe si <Ten>" khong nam trong lich su cua user
    explicit_unknown = _extract_explicit_unknown_artist_name(query_text)
    if explicit_unknown:
        return explicit_unknown, "explicit_unheard"

    return None, "none"


def _resolve_artist_queryset(user, artist_name: str, start_date: str, end_date: str):
    """Tao queryset ListeningHistory chi doc, co lap theo user + artist_name + khoang ngay."""
    s_d = _parse_iso_date(start_date)
    e_d = _parse_iso_date(end_date)
    if not s_d or not e_d or s_d > e_d:
        raise ValueError("Khoảng ngày start_date/end_date không hợp lệ.")

    start_dt, end_dt = _date_bounds_aware(s_d, e_d)
    norm_target = normalize_vi_text(artist_name)

    matched_artist = None
    for art in _get_user_listened_artists(user):
        if normalize_vi_text(art.name) == norm_target:
            matched_artist = art
            break

    if not matched_artist:
        return None, ListeningHistory.objects.none(), start_dt, end_dt, s_d, e_d

    qs = ListeningHistory.objects.filter(
        user=user,
        track__artists=matched_artist,
        played_at__gte=start_dt,
        played_at__lte=end_dt,
    )
    return matched_artist, qs, start_dt, end_dt, s_d, e_d


def tool_artist_listening_overview(
    user,
    artist_name: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Sub-tool 1: Tong hop cot loi cho 1 nghe si trong khoang [start_date, end_date]:
    tong so luot nghe, ty trong %, thoi luong uoc tinh, ten & so luot bai hat nghe nhieu nhat.
    """
    artist_obj, qs, start_dt, end_dt, _, _ = _resolve_artist_queryset(
        user, artist_name, start_date, end_date
    )
    resolved_name = artist_obj.name if artist_obj else artist_name

    period_total_plays = ListeningHistory.objects.filter(
        user=user,
        played_at__gte=start_dt,
        played_at__lte=end_dt,
    ).count()

    if not artist_obj:
        return {
            "found_artist": False,
            "artist_name": resolved_name,
            "start_date": start_date,
            "end_date": end_date,
            "total_plays": 0,
            "period_total_plays": period_total_plays,
            "share_percentage": 0.0,
            "estimated_duration_ms": 0,
            "estimated_duration_label": "0 phút",
            "unique_tracks_count": 0,
            "active_days_count": 0,
            "top_track_name": None,
            "top_track_plays": 0,
        }

    agg = qs.aggregate(
        total_plays=Count("id", distinct=True),
        total_duration_ms=Sum("track__duration_ms"),
        unique_tracks=Count("track_id", distinct=True),
        active_days=Count(TruncDate("played_at"), distinct=True),
    )
    total_plays = int(agg.get("total_plays") or 0)
    total_duration_ms = int(agg.get("total_duration_ms") or 0)
    share_pct = round((total_plays / period_total_plays) * 100, 1) if period_total_plays > 0 else 0.0

    top_track_row = (
        qs.values("track__name")
        .annotate(play_count=Count("id", distinct=True))
        .order_by("-play_count", "track__name")
        .first()
    )

    return {
        "found_artist": True,
        "artist_name": resolved_name,
        "start_date": start_date,
        "end_date": end_date,
        "total_plays": total_plays,
        "period_total_plays": period_total_plays,
        "share_percentage": share_pct,
        "estimated_duration_ms": total_duration_ms,
        "estimated_duration_label": _format_duration_vi(total_duration_ms),
        "unique_tracks_count": int(agg.get("unique_tracks") or 0),
        "active_days_count": int(agg.get("active_days") or 0),
        "top_track_name": top_track_row["track__name"] if top_track_row else None,
        "top_track_plays": int(top_track_row["play_count"]) if top_track_row else 0,
    }


def tool_artist_top_tracks(
    user,
    artist_name: str,
    start_date: str,
    end_date: str,
    limit: int = 5,
) -> dict:
    """
    Sub-tool 2: Bang xep hang cac bai hat nghe nhieu nhat cua rieng 1 nghe si trong khoang thoi gian.
    """
    artist_obj, qs, _, _, _, _ = _resolve_artist_queryset(user, artist_name, start_date, end_date)
    resolved_name = artist_obj.name if artist_obj else artist_name

    if not artist_obj:
        return {
            "artist_name": resolved_name,
            "start_date": start_date,
            "end_date": end_date,
            "top_track_name": None,
            "top_track_plays": 0,
            "tracks": [],
        }

    rows = list(
        qs.values("track__name", "track__album__name")
        .annotate(
            play_count=Count("id", distinct=True),
            duration_ms=Sum("track__duration_ms"),
        )
        .order_by("-play_count", "track__name")[: max(1, min(limit, 10))]
    )
    tracks = [
        {
            "name": r["track__name"],
            "album": r["track__album__name"] or "",
            "play_count": int(r["play_count"] or 0),
            "estimated_duration_label": _format_duration_vi(int(r["duration_ms"] or 0)),
        }
        for r in rows
    ]

    return {
        "artist_name": resolved_name,
        "start_date": start_date,
        "end_date": end_date,
        "top_track_name": tracks[0]["name"] if tracks else None,
        "top_track_plays": tracks[0]["play_count"] if tracks else 0,
        "tracks": tracks,
    }


def tool_artist_listening_habits(
    user,
    artist_name: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Sub-tool 3: Thoi quen, ngay cao diem va khung gio nghe cua rieng 1 nghe si trong khoang thoi gian.
    """
    artist_obj, qs, _, _, _, _ = _resolve_artist_queryset(user, artist_name, start_date, end_date)
    resolved_name = artist_obj.name if artist_obj else artist_name

    if not artist_obj:
        return {
            "artist_name": resolved_name,
            "start_date": start_date,
            "end_date": end_date,
            "active_days_count": 0,
            "peak_day": None,
            "peak_day_plays": 0,
            "peak_hour_window": None,
            "peak_hour_plays": 0,
            "first_played_at": None,
            "last_played_at": None,
        }

    bounds = qs.aggregate(first_at=Min("played_at"), last_at=Max("played_at"))
    day_rows = list(
        qs.annotate(play_day=TruncDate("played_at"))
        .values("play_day")
        .annotate(cnt=Count("id", distinct=True))
        .order_by("-cnt", "-play_day")
    )
    hour_row = (
        qs.annotate(play_hour=ExtractHour("played_at"))
        .values("play_hour")
        .annotate(cnt=Count("id", distinct=True))
        .order_by("-cnt", "play_hour")
        .first()
    )

    peak_day_str = day_rows[0]["play_day"].isoformat() if day_rows and day_rows[0]["play_day"] else None
    peak_day_plays = int(day_rows[0]["cnt"]) if day_rows else 0
    peak_hour_window = None
    peak_hour_plays = 0
    if hour_row and hour_row["play_hour"] is not None:
        h = int(hour_row["play_hour"])
        peak_hour_window = f"{h:02d}:00-{(h + 1) % 24:02d}:00"
        peak_hour_plays = int(hour_row["cnt"] or 0)

    user_tz = timezone.get_current_timezone()
    first_at = timezone.localtime(bounds["first_at"], user_tz).isoformat() if bounds.get("first_at") else None
    last_at = timezone.localtime(bounds["last_at"], user_tz).isoformat() if bounds.get("last_at") else None

    return {
        "artist_name": resolved_name,
        "start_date": start_date,
        "end_date": end_date,
        "active_days_count": len(day_rows),
        "peak_day": peak_day_str,
        "peak_day_plays": peak_day_plays,
        "peak_hour_window": peak_hour_window,
        "peak_hour_plays": peak_hour_plays,
        "first_played_at": first_at,
        "last_played_at": last_at,
    }


def tool_artist_period_comparison(
    user,
    artist_name: str,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Sub-tool 4: So sanh luot nghe cua rieng 1 nghe si voi khoang thoi gian lien truoc tuong duong.
    """
    artist_obj, qs, _, _, s_d, e_d = _resolve_artist_queryset(user, artist_name, start_date, end_date)
    resolved_name = artist_obj.name if artist_obj else artist_name

    span_days = max((e_d - s_d).days, 0)
    prev_end = s_d - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span_days)
    prev_start_dt, prev_end_dt = _date_bounds_aware(prev_start, prev_end)

    current_plays = qs.count() if artist_obj else 0
    previous_plays = (
        ListeningHistory.objects.filter(
            user=user,
            track__artists=artist_obj,
            played_at__gte=prev_start_dt,
            played_at__lte=prev_end_dt,
        ).count()
        if artist_obj
        else 0
    )

    if current_plays == 0 and previous_plays == 0:
        baseline_status = "empty"
        growth_pct = None
    elif previous_plays == 0 and current_plays > 0:
        baseline_status = "new_activity"
        growth_pct = None
    else:
        baseline_status = "normal"
        growth_pct = round(((current_plays - previous_plays) / previous_plays) * 100, 1)

    return {
        "artist_name": resolved_name,
        "start_date": start_date,
        "end_date": end_date,
        "current_plays": current_plays,
        "previous_plays": previous_plays,
        "previous_start_date": prev_start.isoformat(),
        "previous_end_date": prev_end.isoformat(),
        "growth_percentage": growth_pct,
        "baseline_status": baseline_status,
    }


def collect_artist_subtools_bundle(
    user,
    artist_name: str,
    start_date: str,
    end_date: str,
    norm_q: str,
    top_k: int = 5,
) -> dict:
    """
    Dieu phoi cac sub-tool nghe si theo dung y dinh cau hoi va sinh bo Evidence khop trong tam.
    """
    overview = tool_artist_listening_overview(user, artist_name, start_date, end_date)
    resolved_name = overview["artist_name"]
    tools_used = ["artist_listening_overview"]
    artist_data: dict = {"overview": overview}
    evidence: list[AssistantEvidenceItem] = []

    wants_tracks = any(
        k in norm_q
        for k in ("bai hat", "bai nao", "ca khuc", "top", "nhieu nhat", "tong hop", "chi tiet", "nghe gi")
    )
    wants_duration = any(
        k in norm_q
        for k in ("thoi luong", "thoi gian", "bao lau", "may gio", "tong hop", "chi tiet", "tong ket")
    )
    wants_habits = any(
        k in norm_q
        for k in ("khung gio", "may gio", "khi nao", "thoi quen", "ngay nao", "cao diem", "ban dem")
    )
    wants_compare = any(
        k in norm_q
        for k in ("so sanh", "tang", "giam", "xu huong", "ky truoc", "tuan truoc", "thang truoc", "nam truoc")
    )

    if not overview["found_artist"]:
        evidence.append(
            AssistantEvidenceItem(
                label=f"Nghệ sĩ: {resolved_name}",
                value="Chưa có trong lịch sử nghe",
                detail=f"Không tìm thấy lượt phát của {resolved_name} trong tài khoản của bạn",
                is_estimate=False,
                category="observed",
            )
        )
        return {
            "artist_focus": artist_data,
            "evidence": evidence,
            "tools_used": tools_used,
            "resolved_artist_name": resolved_name,
            "top_track_name": None,
        }

    evidence.append(
        AssistantEvidenceItem(
            label=f"Lượt nghe {resolved_name}",
            value=f"{overview['total_plays']:,} lượt",
            detail=(
                f"Chiếm {overview['share_percentage']}% tổng lượt phát kỳ này • "
                f"{overview['unique_tracks_count']} bài hát khác nhau"
                if overview["total_plays"] > 0
                else f"0 lượt phát trong giai đoạn {start_date} đến {end_date}"
            ),
            is_estimate=False,
            category="observed",
        )
    )

    if overview["top_track_name"] and overview["total_plays"] > 0:
        evidence.append(
            AssistantEvidenceItem(
                label=f"Bài nghe nhiều nhất ({resolved_name})",
                value=overview["top_track_name"],
                detail=f"{overview['top_track_plays']:,} lượt phát trong khoảng thời gian đã chọn",
                is_estimate=False,
                category="observed",
            )
        )

    if wants_duration and overview["total_plays"] > 0:
        evidence.append(
            AssistantEvidenceItem(
                label=f"Thời lượng nghe {resolved_name} (ước tính)",
                value=overview["estimated_duration_label"],
                detail="Cộng dồn từ độ dài chuẩn các bài hát đã phát của nghệ sĩ này",
                is_estimate=True,
                category="estimate",
            )
        )

    if wants_tracks and overview["total_plays"] > 0:
        tools_used.append("artist_top_tracks")
        artist_data["top_tracks"] = tool_artist_top_tracks(
            user, resolved_name, start_date, end_date, limit=top_k
        )

    if wants_habits and overview["total_plays"] > 0:
        tools_used.append("artist_listening_habits")
        habits = tool_artist_listening_habits(user, resolved_name, start_date, end_date)
        artist_data["habits"] = habits
        if habits.get("peak_hour_window") or habits.get("peak_day"):
            habit_val = habits.get("peak_hour_window") or habits.get("peak_day") or "-"
            detail_parts = []
            if habits.get("peak_hour_plays"):
                detail_parts.append(f"{habits['peak_hour_plays']} lượt ở khung giờ cao điểm")
            if habits.get("peak_day"):
                detail_parts.append(f"ngày cao điểm {habits['peak_day']} ({habits['peak_day_plays']} lượt)")
            evidence.append(
                AssistantEvidenceItem(
                    label=f"Thói quen nghe {resolved_name}",
                    value=habit_val,
                    detail=" • ".join(detail_parts),
                    is_estimate=False,
                    category="observed",
                )
            )

    if wants_compare:
        tools_used.append("artist_period_comparison")
        comp = tool_artist_period_comparison(user, resolved_name, start_date, end_date)
        artist_data["comparison"] = comp
        if comp["baseline_status"] == "new_activity":
            comp_val = "Hoạt động mới (kỳ trước: 0 lượt)"
        elif comp["growth_percentage"] is not None:
            sign = "+" if comp["growth_percentage"] > 0 else ""
            comp_val = f"{sign}{comp['growth_percentage']}% (kỳ trước: {comp['previous_plays']:,} lượt)"
        else:
            comp_val = "0 lượt ở cả hai kỳ"
        evidence.append(
            AssistantEvidenceItem(
                label=f"So sánh kỳ trước ({resolved_name})",
                value=comp_val,
                detail=f"Đối chiếu với giai đoạn {comp['previous_start_date']} đến {comp['previous_end_date']}",
                is_estimate=False,
                category="calculated",
            )
        )

    return {
        "artist_focus": artist_data,
        "evidence": evidence,
        "tools_used": tools_used,
        "resolved_artist_name": resolved_name,
        "top_track_name": overview.get("top_track_name"),
    }
