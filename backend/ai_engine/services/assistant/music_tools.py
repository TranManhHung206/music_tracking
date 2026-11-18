"""
Cac cong cu truy van du lieu am nhac chi doc (Read-Only) va co lap theo user (User-Scoped).
Dung cho Music Insights cua Hybrid Assistant, tuyet doi khong tin user_id tu client.
"""

import calendar
from dataclasses import dataclass
from datetime import datetime, time, timedelta, date
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
from .intent_router import normalize_vi_text
from .schemas import AssistantEvidenceItem, AssistantScopeMeta

FEATURE_LABELS_VI = {
    "valence": "Cảm xúc tích cực (Valence)",
    "energy": "Năng lượng (Energy)",
    "danceability": "Độ sôi động / Nhịp nhảy (Danceability)",
    "acousticness": "Chất mộc (Acousticness)",
    "tempo_normalized": "Nhịp độ chuẩn hóa (Tempo)",
}


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


def _make_bounds(start_d: date, end_d: date, period_type: str, label: str, source: str) -> ResolvedPeriod:
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
    )


def resolve_assistant_period(query_text: str, period_context: dict | None = None) -> ResolvedPeriod:
    """
    Xac dinh khoang thoi gian ap dung theo thu tu uu tien:
    1) Thoi gian nguoi dung yeu cau ro trong cau hoi
    2) Ky dang chon tren Dashboard (period_context)
    3) Cua so mac dinh 30 ngay gan nhat
    """
    norm = normalize_vi_text(query_text)
    today = timezone.localdate()

    if "tuan truoc" in norm or "tuan qua" in norm:
        curr_mon = today - timedelta(days=today.weekday())
        prev_mon = curr_mon - timedelta(days=7)
        prev_sun = prev_mon + timedelta(days=6)
        iso_year, iso_week, _ = prev_mon.isocalendar()
        return _make_bounds(prev_mon, prev_sun, "week", f"Tuần {iso_week} ({iso_year})", "requested_in_query")

    if "tuan nay" in norm:
        curr_mon = today - timedelta(days=today.weekday())
        curr_sun = curr_mon + timedelta(days=6)
        return _make_bounds(curr_mon, curr_sun, "week", "Tuần này", "requested_in_query")

    if "thang truoc" in norm:
        prev_year, prev_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        last_day = calendar.monthrange(prev_year, prev_month)[1]
        return _make_bounds(
            date(prev_year, prev_month, 1),
            date(prev_year, prev_month, last_day),
            "month",
            f"Tháng {prev_month:02d}/{prev_year}",
            "requested_in_query",
        )

    if "thang nay" in norm:
        last_day = calendar.monthrange(today.year, today.month)[1]
        return _make_bounds(
            date(today.year, today.month, 1),
            date(today.year, today.month, last_day),
            "month",
            f"Tháng {today.month:02d}/{today.year}",
            "requested_in_query",
        )

    if "nam truoc" in norm or "nam ngoai" in norm:
        py = today.year - 1
        return _make_bounds(date(py, 1, 1), date(py, 12, 31), "year", f"Năm {py}", "requested_in_query")

    if "nam nay" in norm:
        return _make_bounds(date(today.year, 1, 1), date(today.year, 12, 31), "year", f"Năm {today.year}", "requested_in_query")

    if "7 ngay" in norm:
        start_d = today - timedelta(days=6)
        return _make_bounds(start_d, today, "week", "7 ngày gần nhất", "requested_in_query")

    if "30 ngay" in norm:
        start_d = today - timedelta(days=29)
        return _make_bounds(start_d, today, "month", "30 ngày gần nhất", "requested_in_query")

    if isinstance(period_context, dict):
        s_str = str(period_context.get("start_date") or "").strip()
        e_str = str(period_context.get("end_date") or "").strip()
        p_type = str(period_context.get("period_type") or "").strip().lower()
        p_label = str(period_context.get("label") or "").strip()[:80]
        if s_str and e_str:
            try:
                s_date = datetime.strptime(s_str, "%Y-%m-%d").date()
                e_date = datetime.strptime(e_str, "%Y-%m-%d").date()
                if s_date <= e_date and (e_date - s_date).days <= 370:
                    resolved_type = p_type if p_type in ("week", "month", "year") else (
                        "week" if (e_date - s_date).days <= 8 else ("month" if (e_date - s_date).days <= 35 else "year")
                    )
                    fallback_label = p_label or f"{s_date.strftime('%d/%m/%Y')} - {e_date.strftime('%d/%m/%Y')}"
                    return _make_bounds(s_date, e_date, resolved_type, fallback_label, "dashboard_period")
            except ValueError:
                pass

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


def _find_user_seed_track(user, query_text: str, start_dt, end_dt) -> Track | None:
    """
    Chi tim bai hat goc nam trong lich su nghe cua chinh user hien tai.
    Khong cho phep tham do bai hat thuoc user khac.
    """
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


def tool_user_knn_recommendations(user, query_text: str, start_dt, end_dt, top_k: int = 5) -> dict:
    """Goi y bai hat tuong dong bang KNN dua tren bai hat ma chinh user da nghe."""
    seed_track = _find_user_seed_track(user, query_text, start_dt, end_dt)
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


def _detect_requested_tools(norm_q: str) -> set[str]:
    tools = {"summary"}
    wants_top = any(
        k in norm_q
        for k in (
            "top",
            "nhieu nhat",
            "bai hat",
            "bai nao",
            "nhung bai",
            "ca khuc",
            "nghe gi",
            "nghe si",
            "ca si",
            "album",
            "the loai",
            "v-pop",
            "k-pop",
            "edm",
            "gu",
        )
    )
    wants_compare = any(k in norm_q for k in ("so sanh", "tang", "giam", "xu huong", "ky truoc", "tuan truoc", "thang truoc", "nam truoc"))
    wants_radar = any(k in norm_q for k in ("radar", "audio", "dac trung", "valence", "energy", "danceability", "acousticness", "tempo", "gu"))
    wants_patterns = any(k in norm_q for k in ("khung gio", "may gio", "heatmap", "cu dem", "ban dem", "lap lai", "marathon", "thoi quen", "khi nao"))
    wants_rec = any(k in norm_q for k in ("goi y", "tuong tu", "giong bai", "nghe gi tiep", "de xuat"))
    wants_persona = any(k in norm_q for k in ("persona", "ca tinh", "tam ly", "tinh cach"))

    if wants_top:
        tools.add("top_music")
    if wants_compare:
        tools.add("comparison")
    if wants_radar:
        tools.add("audio_features")
    if wants_patterns:
        tools.add("patterns")
    if wants_rec:
        tools.add("recommendations")
    if wants_persona:
        tools.add("persona")

    if len(tools) == 1:
        tools.update({"top_music", "comparison", "audio_features", "patterns"})
    return tools


def collect_music_insights_bundle(
    user,
    query_text: str,
    period_context: dict | None = None,
    top_k: int = 5,
) -> dict:
    """
    Thu thap tong hop so lieu am nhac chi doc cua dung user dang dang nhap.
    Tra ve aggregates an toan, Scope metadata va danh sach Evidence.
    """
    if not user or not getattr(user, "is_authenticated", False):
        raise ValueError("Yêu cầu người dùng đã đăng nhập.")

    resolved = resolve_assistant_period(query_text, period_context)
    norm_q = normalize_vi_text(query_text)
    selected_tools = _detect_requested_tools(norm_q)

    summary_raw = get_listening_summary(user, resolved.start_dt, resolved.end_dt)
    comparison_raw = get_weekly_comparison(
        user,
        resolved.start_dt,
        resolved.end_dt,
        period_type=resolved.period_type,
    )
    comp_summary = comparison_raw.get("summary") or {}

    total_plays = int(summary_raw.get("total_plays") or 0)
    unique_tracks = int(summary_raw.get("unique_tracks_count") or 0)
    unique_artists = int(summary_raw.get("unique_artists_count") or 0)
    unique_albums = int(summary_raw.get("unique_albums_count") or 0)
    total_duration_ms = int(summary_raw.get("total_duration_ms") or 0)
    total_hours = float(summary_raw.get("total_hours") or 0.0)
    duration_text = _format_duration_vi(total_duration_ms, total_hours)

    tools_used = ["user_listening_summary", "period_comparison"]
    evidence: list[AssistantEvidenceItem] = [
        AssistantEvidenceItem(
            label="Lượt phát thực tế",
            value=f"{total_plays:,} lượt",
            detail=f"{unique_tracks} bài hát khác nhau, {unique_artists} nghệ sĩ, {unique_albums} album",
            is_estimate=False,
            category="observed",
        ),
        AssistantEvidenceItem(
            label="Thời lượng ước tính",
            value=duration_text,
            detail="Cộng dồn từ độ dài chuẩn của các bản nhạc đã phát",
            is_estimate=True,
            category="estimate",
        ),
    ]

    growth_pct = comp_summary.get("growth_percentage")
    baseline_status = comp_summary.get("baseline_status", "empty")
    prev_total = int(comp_summary.get("total_previous") or comp_summary.get("total_previous_week") or 0)
    if baseline_status == "new_activity":
        delta_text = f"Hoạt động mới (kỳ trước: 0 lượt)"
    elif growth_pct is not None:
        sign = "+" if growth_pct > 0 else ""
        delta_text = f"{sign}{growth_pct}% so với {comparison_raw.get('previous_label', 'kỳ trước')} ({prev_total} lượt)"
    else:
        delta_text = f"0 lượt ở cả hai kỳ"

    if "comparison" in selected_tools or total_plays > 0:
        evidence.append(
            AssistantEvidenceItem(
                label="So sánh kỳ trước",
                value=delta_text,
                detail=f"Cao điểm: {comp_summary.get('peak_label', '-')} ({comp_summary.get('peak_plays', 0)} lượt)",
                is_estimate=False,
                category="calculated",
            )
        )

    aggregates: dict = {
        "period": {
            "label": resolved.label,
            "start_date": resolved.start_date,
            "end_date": resolved.end_date,
            "period_type": resolved.period_type,
            "scope_source": resolved.source,
        },
        "summary": {
            "total_plays": total_plays,
            "unique_tracks_count": unique_tracks,
            "unique_artists_count": unique_artists,
            "unique_albums_count": unique_albums,
            "estimated_duration_label": duration_text,
            "previous_period_label": comparison_raw.get("previous_label", "Kỳ trước"),
            "previous_period_plays": prev_total,
            "growth_percentage": growth_pct,
            "baseline_status": baseline_status,
            "peak_bucket_label": comp_summary.get("peak_label"),
            "peak_bucket_plays": comp_summary.get("peak_plays", 0),
        },
    }

    if "top_music" in selected_tools and total_plays > 0:
        tools_used.extend(["top_tracks", "top_artists", "top_albums", "genre_distribution"])
        top_tracks = get_top_tracks(user, resolved.start_dt, resolved.end_dt, limit=top_k)
        top_artists = get_top_artists(user, resolved.start_dt, resolved.end_dt, limit=top_k)
        top_albums = get_top_albums(user, resolved.start_dt, resolved.end_dt, limit=top_k)
        genres = get_genre_distribution(user, resolved.start_dt, resolved.end_dt)

        aggregates["top_tracks"] = [
            {
                "name": t["name"],
                "artists": t.get("artists", []),
                "play_count": t["play_count"],
            }
            for t in top_tracks
        ]
        aggregates["top_artists"] = [
            {"name": a["name"], "play_count": a["play_count"]}
            for a in top_artists
        ]
        aggregates["top_albums"] = [
            {"name": al["name"], "artists": al.get("artists", []), "play_count": al["play_count"]}
            for al in top_albums
        ]
        aggregates["genres"] = {
            "top_genre": genres.get("top_genre"),
            "distribution": genres.get("genres", [])[:6],
            "provenance_note": "Phân loại bằng bộ phân tích kết hợp của MusicTrack (siêu dữ liệu + đặc trưng âm thanh).",
        }
        if top_tracks:
            evidence.append(
                AssistantEvidenceItem(
                    label="Bài hát dẫn đầu",
                    value=top_tracks[0]["name"],
                    detail=f"{top_tracks[0]['play_count']} lượt • {', '.join(top_tracks[0].get('artists') or ['Nghệ sĩ'])}",
                    is_estimate=False,
                    category="observed",
                )
            )
        if genres.get("genres"):
            top_g = genres["genres"][0]
            evidence.append(
                AssistantEvidenceItem(
                    label="Thể loại nổi bật (phân loại)",
                    value=f"{top_g['name']} ({top_g['percentage']}%)",
                    detail="Phân loại bằng hệ thống phân tích của MusicTrack",
                    is_estimate=True,
                    category="estimate",
                )
            )

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
                    detail=f"Đo trực tiếp {measured_pct}% số lượt phát"
                    if not has_est
                    else f"Đo trực tiếp {measured_pct}%, phần còn lại có ước lượng/chưa đủ dữ liệu",
                    is_estimate=has_est,
                    category="estimate" if has_est else "calculated",
                )
            )

    if "patterns" in selected_tools and total_plays > 0:
        tools_used.append("listening_patterns")
        heatmap = get_listening_heatmap(
            user, resolved.start_dt, resolved.end_dt, resolved.range_key, period_type=resolved.period_type
        )
        matrix = [c for c in (heatmap.get("matrix") or []) if c.get("count", 0) > 0]
        peak_slots = sorted(matrix, key=lambda c: c["count"], reverse=True)[:3]
        peak_descriptions = [
            f"{DAY_NAMES.get(c['day_of_week'], '')} {c['hour']:02d}:00-{c['hour']+1:02d}:00 ({c['count']} lượt)"
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

    if "recommendations" in selected_tools:
        tools_used.append("knn_recommendations")
        rec_info = tool_user_knn_recommendations(user, query_text, resolved.start_dt, resolved.end_dt, top_k=top_k)
        aggregates["knn_recommendations"] = rec_info
        if rec_info.get("has_seed") and rec_info.get("recommendations"):
            top_rec = rec_info["recommendations"][0]
            evidence.append(
                AssistantEvidenceItem(
                    label="Gợi ý KNN tương đồng nhất",
                    value=f"{top_rec['name']} ({round(top_rec['similarity_score'] * 100)}%)",
                    detail=f"Dựa trên bài gốc: {rec_info['seed_track']['name']}",
                    is_estimate=False,
                    category="calculated",
                )
            )

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

    scope_note = (
        f"Sử dụng kỳ bạn đang chọn trên Dashboard ({resolved.start_date} đến {resolved.end_date})."
        if resolved.source == "dashboard_period"
        else (
            f"Sử dụng khoảng thời gian bạn yêu cầu trong câu hỏi ({resolved.start_date} đến {resolved.end_date})."
            if resolved.source == "requested_in_query"
            else f"Mặc định cửa sổ {resolved.label} ({resolved.start_date} đến {resolved.end_date})."
        )
    )

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
    }
