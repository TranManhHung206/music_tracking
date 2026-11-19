"""
Bo sub-tool chuyen biet tong hop du lieu cho 1 the loai am nhac cu the trong khoang thoi gian.
Dung chung ham classify_artist_genres cua Dashboard de bao dam so lieu nhat quan 100%,
chi doc (Read-Only) va co lap theo tai khoan user dang dang nhap.
"""

import re
from collections import defaultdict
from datetime import datetime, time
from django.db.models import Count
from django.utils import timezone

from analytics.services.calculations import classify_artist_genres, ensure_custom_artists_loaded
from tracker.models import ListeningHistory, Track
from .intent_router import normalize_vi_text
from .schemas import AssistantEvidenceItem

GENRE_ALIAS_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("EDM / Electronic", ("edm / electronic", "edm", "electronic", "nhac dien tu", "dj", "dubstep", "house", "trance", "techno")),
    ("V-Pop", ("v-pop", "vpop", "nhac viet", "pop viet", "v-indie")),
    ("K-Pop", ("k-pop", "kpop", "nhac han", "pop han")),
    ("US-UK / Pop", ("us-uk / pop", "us-uk", "usuk", "nhac au my", "pop au my", "au my")),
    ("Hip-Hop / Rap", ("hip-hop / rap", "hip-hop", "hiphop", "hip hop", "rap")),
    ("Acoustic / Lo-Fi", ("acoustic / lo-fi", "acoustic", "lo-fi", "lofi", "nhac moc", "chill")),
    ("Phonk / High Energy", ("phonk / high energy", "phonk", "high energy", "montagem")),
    ("Russian / CIS Pop", ("russian / cis pop", "russian", "nhac nga", "cis pop")),
    ("Global Pop", ("global pop", "pop quoc te")),
)

GENRE_COREF_PHRASES = (
    "the loai do",
    "dong nhac do",
    "the loai nay",
    "dong nhac nay",
    "loai nhac do",
    "loai nhac nay",
)


def _format_duration_vi(total_duration_ms: int) -> str:
    if total_duration_ms <= 0:
        return "0 phút"
    total_minutes = round(total_duration_ms / 60000)
    if total_minutes < 60:
        return f"{max(total_minutes, 1)} phút"
    hours_val = round(total_duration_ms / 3600000, 2)
    return f"{hours_val} giờ"


def _parse_bounds(start_date: str, end_date: str):
    try:
        s_d = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
        e_d = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Khoảng ngày start_date/end_date không hợp lệ.") from exc
    if s_d > e_d:
        raise ValueError("start_date phải nhỏ hơn hoặc bằng end_date.")
    user_tz = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(s_d, time.min), user_tz),
        timezone.make_aware(datetime.combine(e_d, time.max), user_tz),
    )


def extract_genre_target(
    query_text: str,
    persistent_memory: dict | None = None,
) -> tuple[str | None, str]:
    """
    Anh xa tu khoa the loai trong cau hoi hoac dai tu tham chieu sang ten the loai chuan cua MusicTrack.
    Tra ve (genre_name, source) voi source: 'matched_in_query' | 'session_coref' | 'none'.
    """
    norm_q = normalize_vi_text(query_text)
    for canonical_name, aliases in GENRE_ALIAS_MAP:
        for alias in aliases:
            pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
            if re.search(pattern, norm_q):
                return canonical_name, "matched_in_query"

    active_genre = (persistent_memory or {}).get("active_genre")
    if active_genre and any(cue in norm_q for cue in GENRE_COREF_PHRASES):
        return str(active_genre), "session_coref"

    return None, "none"


def _collect_genre_records(user, genre_name: str, start_date: str, end_date: str) -> dict:
    """
    Truy van 1 luot lich su nghe cua user trong [start_date, end_date] (khong N+1)
    va loc cac ban nhac thuoc dung genre_name bang classify_artist_genres.
    """
    ensure_custom_artists_loaded()
    start_dt, end_dt = _parse_bounds(start_date, end_date)
    track_counts = list(
        ListeningHistory.objects.filter(
            user=user,
            played_at__gte=start_dt,
            played_at__lte=end_dt,
        )
        .values("track_id")
        .annotate(play_count=Count("id"))
    )

    period_total_plays = sum(int(item["play_count"] or 0) for item in track_counts)
    if not track_counts:
        return {
            "genre_name": genre_name,
            "period_total_plays": 0,
            "genre_plays": 0,
            "duration_ms": 0,
            "tracks": [],
            "artists": [],
        }

    track_ids = [item["track_id"] for item in track_counts]
    tracks_map = {
        t.id: t
        for t in Track.objects.filter(id__in=track_ids)
        .select_related("album")
        .prefetch_related("artists")
    }

    genre_plays = 0
    total_duration_ms = 0
    matched_tracks: list[dict] = []
    artist_play_totals: dict[str, int] = defaultdict(int)

    norm_target = normalize_vi_text(genre_name)
    for item in track_counts:
        track = tracks_map.get(item["track_id"])
        if not track:
            continue
        count = int(item["play_count"] or 0)
        artist_names = [a.name for a in track.artists.all()]
        primary_artist = artist_names[0] if artist_names else ""

        classified = classify_artist_genres(
            artist_name=primary_artist,
            track_name=track.name,
            artists=artist_names,
            track=track,
            auto_register=False,
        )
        if normalize_vi_text(classified) != norm_target:
            continue

        genre_plays += count
        track_dur_ms = int(track.duration_ms or 0) * count
        total_duration_ms += track_dur_ms
        matched_tracks.append(
            {
                "name": track.name,
                "artists": artist_names,
                "album": track.album.name if track.album else "",
                "play_count": count,
                "estimated_duration_label": _format_duration_vi(track_dur_ms),
            }
        )
        for art_name in artist_names:
            artist_play_totals[art_name] += count

    matched_tracks.sort(key=lambda t: (-t["play_count"], t["name"]))
    sorted_artists = sorted(artist_play_totals.items(), key=lambda x: (-x[1], x[0]))
    artist_rows = [
        {
            "name": name,
            "play_count": plays,
            "share_in_genre": round((plays / genre_plays) * 100, 1) if genre_plays > 0 else 0.0,
        }
        for name, plays in sorted_artists
    ]

    return {
        "genre_name": genre_name,
        "period_total_plays": period_total_plays,
        "genre_plays": genre_plays,
        "duration_ms": total_duration_ms,
        "tracks": matched_tracks,
        "artists": artist_rows,
    }


def tool_genre_listening_overview(
    user,
    genre_name: str,
    start_date: str,
    end_date: str,
    _precomputed: dict | None = None,
) -> dict:
    """
    Sub-tool 1: Tong hop cot loi cho 1 the loai trong [start_date, end_date]:
    tong luot, ty trong %, thoi luong uoc tinh, nghe si & bai hat dan dau trong the loai do.
    """
    data = _precomputed or _collect_genre_records(user, genre_name, start_date, end_date)
    genre_plays = int(data["genre_plays"])
    period_total = int(data["period_total_plays"])
    share_pct = round((genre_plays / period_total) * 100, 1) if period_total > 0 else 0.0
    top_artist = data["artists"][0] if data["artists"] else None
    top_track = data["tracks"][0] if data["tracks"] else None

    return {
        "genre_name": genre_name,
        "start_date": start_date,
        "end_date": end_date,
        "total_plays": genre_plays,
        "period_total_plays": period_total,
        "share_percentage": share_pct,
        "estimated_duration_ms": int(data["duration_ms"]),
        "estimated_duration_label": _format_duration_vi(int(data["duration_ms"])),
        "unique_tracks_count": len(data["tracks"]),
        "unique_artists_count": len(data["artists"]),
        "top_artist_name": top_artist["name"] if top_artist else None,
        "top_artist_plays": int(top_artist["play_count"]) if top_artist else 0,
        "top_track_name": top_track["name"] if top_track else None,
        "top_track_plays": int(top_track["play_count"]) if top_track else 0,
        "provenance_note": "Phân loại bằng hệ thống kết hợp của MusicTrack (siêu dữ liệu + đặc trưng âm thanh).",
    }


def tool_genre_top_artists(
    user,
    genre_name: str,
    start_date: str,
    end_date: str,
    limit: int = 5,
    _precomputed: dict | None = None,
) -> dict:
    """
    Sub-tool 2: Top nghe si / DJ nghe nhieu nhat trong 1 the loai cu the.
    """
    data = _precomputed or _collect_genre_records(user, genre_name, start_date, end_date)
    artists = data["artists"][: max(1, min(limit, 10))]
    return {
        "genre_name": genre_name,
        "start_date": start_date,
        "end_date": end_date,
        "top_artist_name": artists[0]["name"] if artists else None,
        "top_artist_plays": int(artists[0]["play_count"]) if artists else 0,
        "artists": artists,
    }


def tool_genre_top_tracks(
    user,
    genre_name: str,
    start_date: str,
    end_date: str,
    limit: int = 5,
    _precomputed: dict | None = None,
) -> dict:
    """
    Sub-tool 3: Top bai hat nghe nhieu nhat trong 1 the loai cu the.
    """
    data = _precomputed or _collect_genre_records(user, genre_name, start_date, end_date)
    tracks = data["tracks"][: max(1, min(limit, 10))]
    return {
        "genre_name": genre_name,
        "start_date": start_date,
        "end_date": end_date,
        "top_track_name": tracks[0]["name"] if tracks else None,
        "top_track_plays": int(tracks[0]["play_count"]) if tracks else 0,
        "tracks": tracks,
    }


def collect_genre_subtools_bundle(
    user,
    genre_name: str,
    start_date: str,
    end_date: str,
    norm_q: str,
    top_k: int = 5,
) -> dict:
    """
    Dieu phoi cac sub-tool the loai theo dung cau hoi va chi sinh Evidence cho dung the loai yeu cau.
    """
    precomputed = _collect_genre_records(user, genre_name, start_date, end_date)
    overview = tool_genre_listening_overview(
        user, genre_name, start_date, end_date, _precomputed=precomputed
    )
    tools_used = ["genre_listening_overview"]
    genre_data: dict = {"overview": overview}
    evidence: list[AssistantEvidenceItem] = []

    wants_artists = any(
        k in norm_q
        for k in ("dj", "nghe si", "ca si", "ban nhac", "artist", "ai", "nao", "top", "tong hop", "chi tiet")
    )
    wants_tracks = any(
        k in norm_q
        for k in ("bai hat", "bai nao", "ca khuc", "track", "tong hop", "chi tiet")
    )

    evidence.append(
        AssistantEvidenceItem(
            label=f"Thể loại: {genre_name}",
            value=f"{overview['total_plays']:,} lượt ({overview['share_percentage']}%)",
            detail=(
                f"{overview['unique_artists_count']} nghệ sĩ, {overview['unique_tracks_count']} bài hát • Phân loại bởi MusicTrack"
                if overview["total_plays"] > 0
                else f"0 lượt phát thuộc thể loại {genre_name} trong giai đoạn {start_date} đến {end_date}"
            ),
            is_estimate=True,
            category="estimate",
        )
    )

    if wants_artists and overview["total_plays"] > 0:
        tools_used.append("genre_top_artists")
        top_artists_res = tool_genre_top_artists(
            user, genre_name, start_date, end_date, limit=top_k, _precomputed=precomputed
        )
        genre_data["top_artists"] = top_artists_res
        if top_artists_res.get("top_artist_name"):
            evidence.append(
                AssistantEvidenceItem(
                    label=f"Nghệ sĩ nổi bật ({genre_name})",
                    value=top_artists_res["top_artist_name"],
                    detail=f"{top_artists_res['top_artist_plays']:,} lượt phát thuộc thể loại {genre_name}",
                    is_estimate=False,
                    category="observed",
                )
            )

    if wants_tracks and overview["total_plays"] > 0:
        tools_used.append("genre_top_tracks")
        top_tracks_res = tool_genre_top_tracks(
            user, genre_name, start_date, end_date, limit=top_k, _precomputed=precomputed
        )
        genre_data["top_tracks"] = top_tracks_res
        if top_tracks_res.get("top_track_name"):
            evidence.append(
                AssistantEvidenceItem(
                    label=f"Bài hát nổi bật ({genre_name})",
                    value=top_tracks_res["top_track_name"],
                    detail=f"{top_tracks_res['top_track_plays']:,} lượt phát thuộc thể loại {genre_name}",
                    is_estimate=False,
                    category="observed",
                )
            )

    return {
        "genre_focus": genre_data,
        "evidence": evidence,
        "tools_used": tools_used,
        "resolved_genre_name": genre_name,
        "top_artist_name": overview.get("top_artist_name"),
        "top_track_name": overview.get("top_track_name"),
    }
