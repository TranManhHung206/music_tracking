"""
Cac cong cu truy van du lieu am nhac chi doc (Read-Only) va co lap theo user (User-Scoped).
Ho tro goi tool chon loc theo dung y dinh cau hoi, sub-tool nghe si, sub-tool the loai,
ke thua pham vi thoi gian tu Session Persistent Memory va sinh Evidence khop trong tam.
"""

import re
from dataclasses import dataclass
from datetime import datetime, time, date
from django.utils import timezone

from analytics.services.filters import get_time_range_bounds
from analytics.services.calculations import (
    DAY_NAMES,
    get_listening_summary,
    get_top_tracks,
    get_top_artists,
    get_top_albums,
    get_genre_distribution,
    get_radar_features,
    get_listening_heatmap,
    get_weekly_comparison,
)
from ai_engine.models import AIMusicPersona
from ai_engine.services.knn_recommender import get_song_recommendations
from ai_engine.services.facts_agent.tools import (
    query_repeat_loops,
    query_night_owl_anomaly,
    query_marathon_sessions,
)
from tracker.models import ListeningHistory, Track
from .artist_tools import (
    collect_artist_subtools_bundle,
    extract_artist_target,
    extract_date_range_from_text,
    try_extract_artist_params_with_llm,
)
from .genre_tools import (
    collect_genre_subtools_bundle,
    extract_genre_target,
)
from .intent_router import normalize_vi_text
from .schemas import AssistantEvidenceItem, AssistantScopeMeta

FEATURE_LABELS_VI = {
    "valence": "Cảm xúc tích cực (Valence)",
    "energy": "Năng lượng (Energy)",
    "danceability": "Độ sôi động / Nhịp nhảy (Danceability)",
    "acousticness": "Chất mộc (Acousticness)",
    "tempo_normalized": "Nhịp độ chuẩn hóa (Tempo)",
}

COMPLEX_DATE_HINTS = (
    "dau nam",
    "cuoi nam",
    "nua dau",
    "nua cuoi",
    "giua thang",
    "dau thang",
    "cuoi thang",
    "tu luc",
    "tu khi",
)


@dataclass
class ResolvedPeriod:
    start_dt: datetime
    end_dt: datetime
    range_key: str
    period_type: str
    label: str
    start_date: str
    end_date: str
    source: str
    inherited_from_session: bool = False


def _make_bounds(
    start_d: date,
    end_d: date,
    period_type: str,
    label: str,
    source: str,
    inherited_from_session: bool = False,
) -> ResolvedPeriod:
    user_tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_d, time.min), user_tz)
    end_dt = timezone.make_aware(datetime.combine(end_d, time.max), user_tz)
    return ResolvedPeriod(
        start_dt=start_dt,
        end_dt=end_dt,
        range_key=f"period_{start_d.isoformat()}_{end_d.isoformat()}",
        period_type=period_type,
        label=label,
        start_date=start_d.isoformat(),
        end_date=end_d.isoformat(),
        source=source,
        inherited_from_session=inherited_from_session,
    )


def _extract_dashboard_bounds(period_context: dict | None) -> dict | None:
    if not isinstance(period_context, dict):
        return None
    s_str = str(period_context.get("start_date") or "").strip()
    e_str = str(period_context.get("end_date") or "").strip()
    if not s_str or not e_str:
        return None
    try:
        s_d = datetime.strptime(s_str, "%Y-%m-%d").date()
        e_d = datetime.strptime(e_str, "%Y-%m-%d").date()
        if s_d <= e_d and (e_d - s_d).days <= 731:
            return {"start_date": s_d.isoformat(), "end_date": e_d.isoformat()}
    except ValueError:
        return None
    return None


def _parse_period_dict(
    raw_ctx: dict | None,
    fallback_source: str,
    inherited_from_session: bool = False,
) -> ResolvedPeriod | None:
    if not isinstance(raw_ctx, dict):
        return None
    s_str = str(raw_ctx.get("start_date") or "").strip()
    e_str = str(raw_ctx.get("end_date") or "").strip()
    p_type = str(raw_ctx.get("period_type") or "").strip().lower()
    p_label = str(raw_ctx.get("label") or "").strip()[:80]
    if not s_str or not e_str:
        return None
    try:
        s_date = datetime.strptime(s_str, "%Y-%m-%d").date()
        e_date = datetime.strptime(e_str, "%Y-%m-%d").date()
        if s_date <= e_date and (e_date - s_date).days <= 731:
            resolved_type = (
                p_type
                if p_type in ("week", "month", "year")
                else ("week" if (e_date - s_date).days <= 8 else ("month" if (e_date - s_date).days <= 35 else "year"))
            )
            label = p_label or f"{s_date.strftime('%d/%m/%Y')} - {e_date.strftime('%d/%m/%Y')}"
            src = str(raw_ctx.get("source") or fallback_source)
            if src not in ("dashboard_period", "requested_in_query", "rolling_window"):
                src = fallback_source
            return _make_bounds(
                s_date,
                e_date,
                resolved_type,
                label,
                src,
                inherited_from_session=inherited_from_session,
            )
    except ValueError:
        return None
    return None


def resolve_assistant_period(
    query_text: str,
    period_context: dict | None = None,
    persistent_memory: dict | None = None,
    llm_dates: tuple[str | None, str | None] | None = None,
) -> ResolvedPeriod:
    """
    Xac dinh khoang thoi gian ap dung theo thu tu uu tien:
    1) Khoang thoi gian nguoi dung yeu cau ro trong cau hoi (tang 1 regex / tang 2 LLM)
    2) Sticky Session Period: ke thua active_period trong Session Persistent Memory
       neu nguoi dung khong doi ky tren Dashboard so voi luot truoc
    3) Ky dang chon tren Dashboard (period_context)
    4) Cua so mac dinh 30 ngay gan nhat
    """
    extracted = extract_date_range_from_text(query_text)
    if extracted:
        s_d, e_d, p_type, label = extracted
        return _make_bounds(s_d, e_d, p_type, label, "requested_in_query")

    if llm_dates and llm_dates[0] and llm_dates[1]:
        llm_period = _parse_period_dict(
            {"start_date": llm_dates[0], "end_date": llm_dates[1], "source": "requested_in_query"},
            fallback_source="requested_in_query",
        )
        if llm_period:
            return llm_period

    pm = persistent_memory if isinstance(persistent_memory, dict) else {}
    curr_dash = _extract_dashboard_bounds(period_context)
    prev_dash = pm.get("last_dashboard_period") if isinstance(pm.get("last_dashboard_period"), dict) else None
    dashboard_changed = bool(
        curr_dash
        and prev_dash
        and (curr_dash["start_date"], curr_dash["end_date"])
        != (prev_dash.get("start_date"), prev_dash.get("end_date"))
    )

    active_period = pm.get("active_period")
    if (
        not dashboard_changed
        and isinstance(active_period, dict)
        and active_period.get("source") == "requested_in_query"
    ):
        inherited = _parse_period_dict(
            active_period,
            fallback_source="requested_in_query",
            inherited_from_session=True,
        )
        if inherited:
            return inherited

    dashboard_resolved = _parse_period_dict(period_context, fallback_source="dashboard_period")
    if dashboard_resolved:
        return dashboard_resolved

    start_dt, end_dt, range_key = get_time_range_bounds("30d")
    user_tz = timezone.get_current_timezone()
    s_local = timezone.localtime(start_dt, user_tz).date()
    e_local = timezone.localtime(end_dt, user_tz).date()
    return ResolvedPeriod(
        start_dt=start_dt,
        end_dt=end_dt,
        range_key=range_key,
        period_type="month",
        label="30 ngày gần nhất",
        start_date=s_local.isoformat(),
        end_date=e_local.isoformat(),
        source="rolling_window",
    )


def _format_duration_vi(total_duration_ms: int, total_hours: float) -> str:
    if total_duration_ms <= 0 and total_hours <= 0:
        return "0 phút"
    total_minutes = round(total_duration_ms / 60000) if total_duration_ms > 0 else round(total_hours * 60)
    if total_minutes < 60:
        return f"{max(total_minutes, 1)} phút"
    hours_val = round(total_duration_ms / 3600000, 2) if total_duration_ms > 0 else round(total_hours, 2)
    return f"{hours_val} giờ"


def _slug_key(text: str) -> str:
    norm = normalize_vi_text(text)
    return re.sub(r"[^a-z0-9]+", "_", norm).strip("_")[:28] or "item"


def _find_user_seed_track(
    user,
    query_text: str,
    start_dt,
    end_dt,
    session_entities: dict | None = None,
) -> Track | None:
    """Chi tim bai hat goc nam trong lich su nghe cua chinh user hien tai."""
    norm_q = normalize_vi_text(query_text)
    user_track_ids = list(
        ListeningHistory.objects.filter(user=user)
        .values_list("track_id", flat=True)
        .distinct()[:250]
    )
    if not user_track_ids:
        return None

    candidate_tracks = list(
        Track.objects.filter(id__in=user_track_ids).prefetch_related("artists")
    )
    for trk in candidate_tracks:
        norm_name = normalize_vi_text(trk.name)
        if len(norm_name) >= 3 and norm_name in norm_q:
            return trk

    last_track = (session_entities or {}).get("last_track")
    if last_track and any(k in norm_q for k in ("bai do", "bai hat do", "bai nay", "ca khuc do")):
        norm_last = normalize_vi_text(str(last_track))
        for trk in candidate_tracks:
            if normalize_vi_text(trk.name) == norm_last:
                return trk

    top_in_period = get_top_tracks(user, start_dt, end_dt, limit=1)
    if top_in_period and top_in_period[0].get("spotify_id"):
        matched = Track.objects.filter(
            id__in=user_track_ids,
            spotify_id=top_in_period[0]["spotify_id"],
        ).first()
        if matched:
            return matched

    latest_lh = (
        ListeningHistory.objects.filter(user=user)
        .select_related("track")
        .order_by("-played_at")
        .first()
    )
    return latest_lh.track if latest_lh else None


def tool_user_knn_recommendations(
    user,
    query_text: str,
    start_dt,
    end_dt,
    top_k: int = 5,
    session_entities: dict | None = None,
) -> dict:
    """Goi y bai hat tuong dong bang KNN dua tren bai hat ma chinh user da nghe."""
    seed_track = _find_user_seed_track(user, query_text, start_dt, end_dt, session_entities)
    if not seed_track:
        return {
            "has_seed": False,
            "reason": "Tài khoản chưa có bài hát nào trong lịch sử nghe để làm mẫu gợi ý.",
            "recommendations": [],
        }

    try:
        knn_result = get_song_recommendations(seed_track.spotify_id, top_k=top_k)
    except ValueError as exc:
        return {
            "has_seed": False,
            "reason": str(exc),
            "recommendations": [],
        }

    seed_info = knn_result.get("seed_track", {})
    recs = knn_result.get("recommendations", [])
    return {
        "has_seed": True,
        "seed_track": {
            "name": seed_info.get("name"),
            "artists": seed_info.get("artists", []),
            "features_source": getattr(seed_track, "features_source", "unavailable"),
            "audio_features": seed_info.get("audio_features", {}),
        },
        "recommendations": [
            {
                "name": r.get("name"),
                "artists": r.get("artists", []),
                "album": r.get("album", ""),
                "similarity_score": r.get("similarity_score", 0.0),
            }
            for r in recs[:top_k]
        ],
        "method_note": "So sánh vector 5 đặc trưng (Danceability, Energy, Valence, Acousticness, Tempo) bằng thuật toán KNN có trọng số.",
    }


def _detect_requested_tools(
    norm_q: str,
    has_artist_target: bool = False,
    has_genre_target: bool = False,
) -> set[str]:
    """Chon loc chinh xac cac tool lien quan den cau hoi thay vi goi dong loat."""
    tools: set[str] = set()

    if has_artist_target:
        tools.add("artist_summary")
    elif has_genre_target:
        tools.add("genre_summary")

    wants_summary = any(
        k in norm_q
        for k in (
            "tong ket",
            "tong quan",
            "bao nhieu luot",
            "tong luot",
            "luot phat",
            "luot nghe",
            "thoi luong",
            "thoi gian nghe",
            "bao nhieu gio",
            "bao nhieu phut",
            "bao lau",
        )
    )
    wants_artists = any(k in norm_q for k in ("nghe si", "ca si", "ban nhac", "artist"))
    wants_tracks = any(k in norm_q for k in ("bai hat", "bai nao", "nhung bai", "ca khuc", "track", "nghe gi"))
    wants_albums = any(k in norm_q for k in ("album", "dia don"))
    wants_genres = any(k in norm_q for k in ("the loai", "dong nhac", "loai nhac", "gu nhac", "gu am nhac", "gu nghe"))
    wants_compare = any(
        k in norm_q
        for k in ("so sanh", "tang", "giam", "xu huong", "ky truoc", "tuan truoc", "thang truoc", "nam truoc")
    )
    wants_radar = any(
        k in norm_q
        for k in (
            "radar",
            "audio",
            "dac trung",
            "chi so am thanh",
            "valence",
            "energy",
            "danceability",
            "acousticness",
            "tempo",
            "bpm",
            "gu nhac",
            "gu am nhac",
            "gu nghe",
        )
    )
    wants_patterns = any(
        k in norm_q
        for k in ("khung gio", "may gio", "heatmap", "cu dem", "ban dem", "lap lai", "marathon", "thoi quen", "khi nao")
    )
    wants_rec = any(k in norm_q for k in ("goi y", "tuong tu", "giong bai", "nghe gi tiep", "de xuat"))
    wants_persona = any(k in norm_q for k in ("persona", "ca tinh", "tam ly", "tinh cach"))

    if not has_artist_target and not has_genre_target:
        if wants_summary:
            tools.add("summary")
        if wants_artists:
            tools.add("top_artists")
        if wants_tracks:
            tools.add("top_tracks")
        if wants_albums:
            tools.add("top_albums")
        if wants_genres:
            tools.add("genres")
        if wants_compare:
            tools.add("comparison")
        if wants_patterns:
            tools.add("patterns")

    if wants_radar:
        tools.add("audio_features")
    if wants_rec:
        tools.add("recommendations")
    if wants_persona:
        tools.add("persona")

    if not tools:
        tools.update({"summary", "top_tracks", "top_artists"})

    return tools


def collect_music_insights_bundle(
    user,
    query_text: str,
    period_context: dict | None = None,
    top_k: int = 5,
    session_entities: dict | None = None,
    persistent_memory: dict | None = None,
) -> dict:
    """
    Thu thap chon loc so lieu am nhac chi doc cua dung user dang dang nhap.
    Tra ve aggregates, Scope metadata, Evidence khop cau hoi va memory_baseline_ops.
    """
    if not user or not getattr(user, "is_authenticated", False):
        raise ValueError("Yêu cầu người dùng đã đăng nhập.")

    norm_q = normalize_vi_text(query_text)
    pm = persistent_memory if isinstance(persistent_memory, dict) else {}
    entities_view = dict(session_entities or {})
    if pm.get("active_artist") and not entities_view.get("last_artist"):
        entities_view["last_artist"] = pm["active_artist"]
    if pm.get("active_track") and not entities_view.get("last_track"):
        entities_view["last_track"] = pm["active_track"]
    if pm.get("active_genre") and not entities_view.get("last_genre"):
        entities_view["last_genre"] = pm["active_genre"]

    artist_name, artist_source = extract_artist_target(user, query_text, entities_view)
    genre_name, genre_source = extract_genre_target(query_text, pm)

    # Chi kich hoat tang 2 LLM khi cau hoi co dau hieu moc ngay phuc tap ma tang 1 chua bat duoc
    llm_dates: tuple[str | None, str | None] | None = None
    if extract_date_range_from_text(query_text) is None and any(h in norm_q for h in COMPLEX_DATE_HINTS):
        extracted_llm = try_extract_artist_params_with_llm(query_text, timezone.localdate().isoformat())
        if extracted_llm:
            if extracted_llm.start_date and extracted_llm.end_date:
                llm_dates = (extracted_llm.start_date, extracted_llm.end_date)
            if not artist_name and extracted_llm.artist_name:
                artist_name = extracted_llm.artist_name
                artist_source = "llm_extracted"

    resolved = resolve_assistant_period(
        query_text,
        period_context=period_context,
        persistent_memory=pm,
        llm_dates=llm_dates,
    )

    has_artist_target = bool(artist_name)
    has_genre_target = bool(genre_name) and not has_artist_target
    selected_tools = _detect_requested_tools(
        norm_q,
        has_artist_target=has_artist_target,
        has_genre_target=has_genre_target,
    )

    summary_raw = get_listening_summary(user, resolved.start_dt, resolved.end_dt)
    total_plays = int(summary_raw.get("total_plays") or 0)
    unique_tracks = int(summary_raw.get("unique_tracks_count") or 0)
    unique_artists = int(summary_raw.get("unique_artists_count") or 0)
    unique_albums = int(summary_raw.get("unique_albums_count") or 0)
    total_duration_ms = int(summary_raw.get("total_duration_ms") or 0)
    total_hours = float(summary_raw.get("total_hours") or 0.0)
    duration_text = _format_duration_vi(total_duration_ms, total_hours)

    tools_used: list[str] = []
    evidence: list[AssistantEvidenceItem] = []

    period_payload = {
        "start_date": resolved.start_date,
        "end_date": resolved.end_date,
        "period_type": resolved.period_type,
        "label": resolved.label,
        "source": resolved.source,
    }
    dash_bounds = _extract_dashboard_bounds(period_context)
    detected_entities: dict = {"last_period": period_payload}
    memory_baseline_ops: list[dict] = [
        {"action": "set", "field": "active_period", "value": period_payload},
    ]
    if dash_bounds:
        detected_entities["last_dashboard_period"] = dash_bounds
        memory_baseline_ops.append(
            {"action": "set", "field": "last_dashboard_period", "value": dash_bounds}
        )

    aggregates: dict = {
        "period": {
            "label": resolved.label,
            "start_date": resolved.start_date,
            "end_date": resolved.end_date,
            "period_type": resolved.period_type,
            "scope_source": resolved.source,
            "inherited_from_session": resolved.inherited_from_session,
        },
        "summary": {
            "total_plays": total_plays,
            "unique_tracks_count": unique_tracks,
            "unique_artists_count": unique_artists,
            "unique_albums_count": unique_albums,
            "estimated_duration_label": duration_text,
        },
    }

    # 1. Nhanh chuyen biet cho 1 nghe si cu the
    if "artist_summary" in selected_tools and artist_name:
        artist_bundle = collect_artist_subtools_bundle(
            user=user,
            artist_name=artist_name,
            start_date=resolved.start_date,
            end_date=resolved.end_date,
            norm_q=norm_q,
            top_k=top_k,
        )
        aggregates["artist_focus"] = artist_bundle["artist_focus"]
        aggregates["artist_focus"]["resolution_source"] = artist_source
        tools_used.extend(artist_bundle["tools_used"])
        evidence.extend(artist_bundle["evidence"])

        res_art = artist_bundle["resolved_artist_name"]
        detected_entities["last_artist"] = res_art
        memory_baseline_ops.append({"action": "set", "field": "active_artist", "value": res_art})
        if artist_bundle.get("top_track_name"):
            detected_entities["last_track"] = artist_bundle["top_track_name"]
            memory_baseline_ops.append(
                {"action": "set", "field": "active_track", "value": artist_bundle["top_track_name"]}
            )
        ov = artist_bundle["artist_focus"].get("overview") or {}
        if ov.get("found_artist"):
            memory_baseline_ops.append(
                {
                    "action": "add",
                    "field": "pinned_facts",
                    "key": f"artist_{_slug_key(res_art)}",
                    "value": (
                        f"{resolved.label}: {res_art} - {ov.get('total_plays', 0)} lượt "
                        f"({ov.get('share_percentage', 0)}%)"
                        + (f", bài nhiều nhất: {ov['top_track_name']} ({ov.get('top_track_plays', 0)} lượt)" if ov.get("top_track_name") else "")
                    ),
                }
            )

    # 2. Nhanh chuyen biet cho 1 the loai cu the
    if "genre_summary" in selected_tools and genre_name:
        genre_bundle = collect_genre_subtools_bundle(
            user=user,
            genre_name=genre_name,
            start_date=resolved.start_date,
            end_date=resolved.end_date,
            norm_q=norm_q,
            top_k=top_k,
        )
        aggregates["genre_focus"] = genre_bundle["genre_focus"]
        aggregates["genre_focus"]["resolution_source"] = genre_source
        tools_used.extend(genre_bundle["tools_used"])
        evidence.extend(genre_bundle["evidence"])

        res_genre = genre_bundle["resolved_genre_name"]
        detected_entities["last_genre"] = res_genre
        memory_baseline_ops.append({"action": "set", "field": "active_genre", "value": res_genre})
        if genre_bundle.get("top_artist_name"):
            detected_entities["last_artist"] = genre_bundle["top_artist_name"]
            memory_baseline_ops.append(
                {"action": "set", "field": "active_artist", "value": genre_bundle["top_artist_name"]}
            )
        if genre_bundle.get("top_track_name"):
            detected_entities["last_track"] = genre_bundle["top_track_name"]
            memory_baseline_ops.append(
                {"action": "set", "field": "active_track", "value": genre_bundle["top_track_name"]}
            )
        g_ov = genre_bundle["genre_focus"].get("overview") or {}
        memory_baseline_ops.append(
            {
                "action": "add",
                "field": "pinned_facts",
                "key": f"genre_{_slug_key(res_genre)}",
                "value": (
                    f"{resolved.label}: {res_genre} - {g_ov.get('total_plays', 0)} lượt ({g_ov.get('share_percentage', 0)}%)"
                    + (f", nổi bật: {g_ov['top_artist_name']} ({g_ov.get('top_artist_plays', 0)} lượt)" if g_ov.get("top_artist_name") else "")
                ),
            }
        )

    # 3. Tong quan toan ky
    if "summary" in selected_tools or (total_plays == 0 and not has_artist_target and not has_genre_target):
        tools_used.append("user_listening_summary")
        evidence.append(
            AssistantEvidenceItem(
                label="Lượt phát thực tế",
                value=f"{total_plays:,} lượt",
                detail=f"{unique_tracks} bài hát khác nhau, {unique_artists} nghệ sĩ, {unique_albums} album",
                is_estimate=False,
                category="observed",
            )
        )
        if total_plays > 0 and (
            "summary" in selected_tools
            and any(k in norm_q for k in ("thoi luong", "thoi gian", "bao lau", "tong ket", "tong quan", "gio", "phut"))
            or len(selected_tools) >= 3
        ):
            evidence.append(
                AssistantEvidenceItem(
                    label="Thời lượng ước tính",
                    value=duration_text,
                    detail="Cộng dồn từ độ dài chuẩn của các bản nhạc đã phát",
                    is_estimate=True,
                    category="estimate",
                )
            )

    # 4. So sanh ky truoc
    if "comparison" in selected_tools and total_plays > 0:
        tools_used.append("period_comparison")
        comparison_raw = get_weekly_comparison(
            user,
            resolved.start_dt,
            resolved.end_dt,
            period_type=resolved.period_type,
        )
        comp_summary = comparison_raw.get("summary") or {}
        growth_pct = comp_summary.get("growth_percentage")
        baseline_status = comp_summary.get("baseline_status", "empty")
        prev_total = int(comp_summary.get("total_previous") or comp_summary.get("total_previous_week") or 0)
        if baseline_status == "new_activity":
            delta_text = "Hoạt động mới (kỳ trước: 0 lượt)"
        elif growth_pct is not None:
            sign = "+" if growth_pct > 0 else ""
            delta_text = f"{sign}{growth_pct}% so với {comparison_raw.get('previous_label', 'kỳ trước')} ({prev_total} lượt)"
        else:
            delta_text = "0 lượt ở cả hai kỳ"

        aggregates["summary"].update(
            {
                "previous_period_label": comparison_raw.get("previous_label", "Kỳ trước"),
                "previous_period_plays": prev_total,
                "growth_percentage": growth_pct,
                "baseline_status": baseline_status,
                "peak_bucket_label": comp_summary.get("peak_label"),
                "peak_bucket_plays": comp_summary.get("peak_plays", 0),
            }
        )
        evidence.append(
            AssistantEvidenceItem(
                label="So sánh kỳ trước",
                value=delta_text,
                detail=f"Cao điểm: {comp_summary.get('peak_label', '-')} ({comp_summary.get('peak_plays', 0)} lượt)",
                is_estimate=False,
                category="calculated",
            )
        )

    # 5. Top Nghe si (doc lap)
    if "top_artists" in selected_tools and total_plays > 0:
        tools_used.append("top_artists")
        top_artists = get_top_artists(user, resolved.start_dt, resolved.end_dt, limit=top_k)
        aggregates["top_artists"] = [
            {
                "name": a["name"],
                "play_count": a["play_count"],
                "share_percentage": round((a["play_count"] / total_plays) * 100, 1) if total_plays > 0 else 0.0,
            }
            for a in top_artists
        ]
        if top_artists:
            lead = top_artists[0]
            share_pct = round((lead["play_count"] / total_plays) * 100, 1) if total_plays > 0 else 0.0
            detected_entities["last_artist"] = lead["name"]
            memory_baseline_ops.append({"action": "set", "field": "active_artist", "value": lead["name"]})
            memory_baseline_ops.append(
                {
                    "action": "add",
                    "field": "pinned_facts",
                    "key": "top_artist",
                    "value": f"{resolved.label}: Nghệ sĩ nghe nhiều nhất là {lead['name']} ({lead['play_count']} lượt, {share_pct}%)",
                }
            )
            evidence.append(
                AssistantEvidenceItem(
                    label="Nghệ sĩ dẫn đầu",
                    value=lead["name"],
                    detail=f"{lead['play_count']:,} lượt ({share_pct}% trên tổng {total_plays:,} lượt kỳ này)",
                    is_estimate=False,
                    category="observed",
                )
            )

    # 6. Top Bai hat (doc lap)
    if "top_tracks" in selected_tools and total_plays > 0:
        tools_used.append("top_tracks")
        top_tracks = get_top_tracks(user, resolved.start_dt, resolved.end_dt, limit=top_k)
        aggregates["top_tracks"] = [
            {
                "name": t["name"],
                "artists": t.get("artists", []),
                "play_count": t["play_count"],
            }
            for t in top_tracks
        ]
        if top_tracks:
            lead_track = top_tracks[0]
            detected_entities["last_track"] = lead_track["name"]
            memory_baseline_ops.append({"action": "set", "field": "active_track", "value": lead_track["name"]})
            if "last_artist" not in detected_entities and lead_track.get("artists"):
                detected_entities["last_artist"] = lead_track["artists"][0]
                memory_baseline_ops.append(
                    {"action": "set", "field": "active_artist", "value": lead_track["artists"][0]}
                )
            evidence.append(
                AssistantEvidenceItem(
                    label="Bài hát dẫn đầu",
                    value=lead_track["name"],
                    detail=f"{lead_track['play_count']:,} lượt • {', '.join(lead_track.get('artists') or ['Nghệ sĩ'])}",
                    is_estimate=False,
                    category="observed",
                )
            )

    # 7. Top Album (doc lap)
    if "top_albums" in selected_tools and total_plays > 0:
        tools_used.append("top_albums")
        top_albums = get_top_albums(user, resolved.start_dt, resolved.end_dt, limit=top_k)
        aggregates["top_albums"] = [
            {"name": al["name"], "artists": al.get("artists", []), "play_count": al["play_count"]}
            for al in top_albums
        ]
        if top_albums:
            lead_alb = top_albums[0]
            evidence.append(
                AssistantEvidenceItem(
                    label="Album dẫn đầu",
                    value=lead_alb["name"],
                    detail=f"{lead_alb['play_count']:,} lượt • {', '.join(lead_alb.get('artists') or ['Nghệ sĩ'])}",
                    is_estimate=False,
                    category="observed",
                )
            )

    # 8. Phan bo tat ca the loai (khi hoi tong the loai khong neu ten 1 the loai cu the)
    if "genres" in selected_tools and total_plays > 0:
        tools_used.append("genre_distribution")
        genres = get_genre_distribution(user, resolved.start_dt, resolved.end_dt)
        aggregates["genres"] = {
            "top_genre": genres.get("top_genre"),
            "distribution": genres.get("genres", [])[:6],
            "provenance_note": "Phân loại bằng bộ phân tích kết hợp của MusicTrack (siêu dữ liệu + đặc trưng âm thanh).",
        }
        if genres.get("genres"):
            top_g = genres["genres"][0]
            detected_entities["last_genre"] = top_g["name"]
            memory_baseline_ops.append({"action": "set", "field": "active_genre", "value": top_g["name"]})
            evidence.append(
                AssistantEvidenceItem(
                    label="Thể loại nổi bật (phân loại)",
                    value=f"{top_g['name']} ({top_g['percentage']}%)",
                    detail="Phân loại bằng hệ thống phân tích của MusicTrack",
                    is_estimate=True,
                    category="estimate",
                )
            )

    # 9. Audio Features Radar
    if "audio_features" in selected_tools and total_plays > 0:
        tools_used.append("audio_features_radar")
        radar = get_radar_features(user, resolved.start_dt, resolved.end_dt, resolved.range_key)
        feats = radar.get("features", [])
        prov = radar.get("provenance", {})
        sorted_feats = sorted(feats, key=lambda x: x.get("score", 0.0), reverse=True)
        top_feat = sorted_feats[0] if sorted_feats else None
        low_feat = sorted_feats[-1] if sorted_feats else None
        aggregates["audio_features"] = {
            "features": feats,
            "highest_trait": top_feat,
            "lowest_trait": low_feat,
            "provenance": prov,
        }
        measured_pct = prov.get("measured_percentage", 0.0)
        has_est = bool(prov.get("has_estimates") or prov.get("has_legacy_unknown") or measured_pct < 100.0)
        if top_feat:
            feat_label = FEATURE_LABELS_VI.get(top_feat["attribute"], top_feat["attribute"])
            evidence.append(
                AssistantEvidenceItem(
                    label="Chỉ số âm thanh nổi bật",
                    value=f"{feat_label}: {round(top_feat['score'] * 100)}%",
                    detail=(
                        f"Đo trực tiếp {measured_pct}% số lượt phát"
                        if not has_est
                        else f"Đo trực tiếp {measured_pct}%, phần còn lại có ước lượng/chưa đủ dữ liệu"
                    ),
                    is_estimate=has_est,
                    category="estimate" if has_est else "calculated",
                )
            )

    # 10. Khung gio & Thoi quen nghe
    if "patterns" in selected_tools and total_plays > 0:
        tools_used.append("listening_patterns")
        heatmap = get_listening_heatmap(
            user, resolved.start_dt, resolved.end_dt, resolved.range_key, period_type=resolved.period_type
        )
        matrix = [c for c in (heatmap.get("matrix") or []) if c.get("count", 0) > 0]
        peak_slots = sorted(matrix, key=lambda c: c["count"], reverse=True)[:3]
        peak_descriptions = [
            f"{DAY_NAMES.get(c['day_of_week'], '')} {c['hour']:02d}:00-{(c['hour'] + 1) % 24:02d}:00 ({c['count']} lượt)"
            for c in peak_slots
        ]
        repeat_data = query_repeat_loops(user, resolved.start_dt, resolved.end_dt, min_repeats=3)
        night_data = query_night_owl_anomaly(user, resolved.start_dt, resolved.end_dt)
        marathon_data = query_marathon_sessions(user, resolved.start_dt, resolved.end_dt)
        aggregates["listening_patterns"] = {
            "peak_windows": peak_descriptions,
            "repeat_loops": repeat_data.get("top_repeats", [])[:3],
            "night_owl": {
                "night_plays_count": night_data.get("night_plays_count", 0),
                "night_percentage": night_data.get("night_percentage", 0.0),
                "is_significant": night_data.get("is_significant_night_owl", False),
            },
            "marathon_session": marathon_data if marathon_data.get("has_data") else None,
        }
        if peak_descriptions:
            evidence.append(
                AssistantEvidenceItem(
                    label="Khung giờ nghe cao điểm",
                    value=peak_descriptions[0],
                    detail="Tính theo múi giờ hiện tại của bạn",
                    is_estimate=False,
                    category="observed",
                )
            )

    # 11. Goi y KNN
    if "recommendations" in selected_tools:
        tools_used.append("knn_recommendations")
        rec_info = tool_user_knn_recommendations(
            user, query_text, resolved.start_dt, resolved.end_dt, top_k=top_k, session_entities=entities_view
        )
        aggregates["knn_recommendations"] = rec_info
        if rec_info.get("has_seed") and rec_info.get("recommendations"):
            top_rec = rec_info["recommendations"][0]
            if rec_info.get("seed_track", {}).get("name"):
                detected_entities["last_track"] = rec_info["seed_track"]["name"]
                memory_baseline_ops.append(
                    {"action": "set", "field": "active_track", "value": rec_info["seed_track"]["name"]}
                )
            evidence.append(
                AssistantEvidenceItem(
                    label="Gợi ý KNN tương đồng nhất",
                    value=f"{top_rec['name']} ({round(top_rec['similarity_score'] * 100)}%)",
                    detail=f"Dựa trên bài gốc: {rec_info['seed_track']['name']}",
                    is_estimate=False,
                    category="calculated",
                )
            )

    # 12. AI Music Persona
    if "persona" in selected_tools:
        tools_used.append("latest_ai_persona")
        persona = AIMusicPersona.objects.filter(user=user).first()
        if persona:
            aggregates["persona_status"] = "available"
            aggregates["latest_persona"] = {
                "persona_title": persona.persona_title,
                "tagline": persona.tagline,
                "vibe_summary": persona.vibe_summary,
                "mood_distribution": persona.mood_distribution,
                "recommended_listening_time": persona.recommended_listening_time,
                "period_type": persona.period_type,
                "note": "Hồ sơ AI Persona tính theo cửa sổ cuộn 30 ngày gần nhất (do AI tổng hợp).",
            }
            evidence.append(
                AssistantEvidenceItem(
                    label="AI Music Persona",
                    value=persona.persona_title,
                    detail="Phân tích diễn giải do AI tổng hợp (cửa sổ 30 ngày)",
                    is_estimate=False,
                    category="ai_interpretation",
                )
            )
        else:
            aggregates["persona_status"] = "missing"

    detected_entities["last_tools"] = tools_used

    if resolved.inherited_from_session:
        scope_note = (
            f"Tiếp tục sử dụng khoảng thời gian từ bộ nhớ phiên ({resolved.label}: "
            f"{resolved.start_date} đến {resolved.end_date})."
        )
    elif resolved.source == "dashboard_period":
        scope_note = f"Sử dụng kỳ bạn đang chọn trên Dashboard ({resolved.start_date} đến {resolved.end_date})."
    elif resolved.source == "requested_in_query":
        scope_note = f"Sử dụng khoảng thời gian bạn yêu cầu trong câu hỏi ({resolved.start_date} đến {resolved.end_date})."
    else:
        scope_note = f"Mặc định cửa sổ {resolved.label} ({resolved.start_date} đến {resolved.end_date})."

    return {
        "resolved": resolved,
        "scope": AssistantScopeMeta(
            label=resolved.label,
            start_date=resolved.start_date,
            end_date=resolved.end_date,
            source=resolved.source,  # type: ignore[arg-type]
            note=scope_note,
        ),
        "aggregates": aggregates,
        "evidence": evidence,
        "tools_used": tools_used,
        "detected_entities": detected_entities,
        "memory_baseline_ops": memory_baseline_ops,
    }
