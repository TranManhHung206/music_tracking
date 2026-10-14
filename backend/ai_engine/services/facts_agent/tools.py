"""
Agent Database Tools cho ung dung ai_engine.
Cac ham truy van co so du lieu bang Django ORM an toan (Read-Only)
phuc vu Aura Music Detective Agent dieu tra lich su nghe nhac.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import ExtractHour, TruncDate
from tracker.models import ListeningHistory, Artist

def query_repeat_loops(user, start_dt, end_dt, min_repeats: int = 3) -> dict:
    """
    Tim kiem cac bai hat duoc nguoi dung nghe lap lai nhieu lan trong cung mot ngay.
    Tra ve danh sach cac bai hat bi 'nghien lap lai' (Repeat Loops).
    """
    user_tz = timezone.get_current_timezone()
    qs = (
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
        )
        .annotate(play_date=TruncDate('played_at', tzinfo=user_tz))
        .values('track__name', 'track__id', 'play_date')
        .annotate(daily_count=Count('id'))
        .filter(daily_count__gte=min_repeats)
        .order_by('-daily_count')[:5]
    )

    results = []
    for item in qs:
        # Lay thong tin nghe si cua bai hat
        track_id = item['track__id']
        sample_record = (
            ListeningHistory.objects.filter(user=user, track_id=track_id)
            .select_related('track')
            .prefetch_related('track__artists')
            .first()
        )
        artist_names = "Nhiều nghệ sĩ"
        if sample_record and sample_record.track:
            artist_names = ", ".join([a.name for a in sample_record.track.artists.all()[:2]]) or "Nghệ sĩ"

        results.append({
            "track_name": item['track__name'],
            "artist_name": artist_names,
            "play_date": item['play_date'].strftime('%d/%m/%Y') if item['play_date'] else "Trong kỳ",
            "repeat_count": item['daily_count'],
        })

    return {
        "tool_name": "query_repeat_loops",
        "has_data": len(results) > 0,
        "loops_found": len(results),
        "top_repeats": results,
    }

def query_night_owl_anomaly(user, start_dt, end_dt) -> dict:
    """
    Dieu tra cac luot nghe nhac trong khung gio dem khuya (00:00 - 05:00 sang).
    Xac dinh xem nguoi dung co thoi quen 'Cu Dem' hay khong va nghe gi vao ban dem.
    """
    total_plays = ListeningHistory.objects.filter(
        user=user,
        played_at__range=(start_dt, end_dt),
    ).count()

    if total_plays == 0:
        return {"tool_name": "query_night_owl_anomaly", "has_data": False, "total_plays": 0}

    user_tz = timezone.get_current_timezone()
    night_records = (
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
        )
        .annotate(play_hour=ExtractHour('played_at', tzinfo=user_tz))
        .filter(play_hour__gte=0, play_hour__lt=5)
    )

    night_plays = night_records.count()
    if night_plays == 0:
        return {
            "tool_name": "query_night_owl_anomaly",
            "has_data": False,
            "night_plays_count": 0,
            "night_percentage": 0.0,
            "is_significant_night_owl": False,
            "tool_note": "Người dùng không nghe nhạc vào ban đêm (0 lượt). Vui lòng bỏ qua công cụ này và gọi công cụ khác (như query_repeat_loops, query_artist_dominance hoặc query_marathon_sessions) để tìm hành vi thực sự nổi bật.",
        }

    night_ratio = round((night_plays / total_plays) * 100, 1)

    # Top nghe si nghe vao ban dem
    top_night_artists = (
        night_records.values('track__artists__name')
        .annotate(cnt=Count('id'))
        .exclude(track__artists__name__isnull=True)
        .order_by('-cnt')[:3]
    )
    night_artist_list = [f"{a['track__artists__name']} ({a['cnt']} lượt)" for a in top_night_artists]

    is_significant = (night_ratio >= 15.0 and night_plays >= 5) or night_plays >= 10

    return {
        "tool_name": "query_night_owl_anomaly",
        "has_data": night_plays > 0,
        "total_period_plays": total_plays,
        "night_plays_count": night_plays,
        "night_percentage": night_ratio,
        "top_night_artists": night_artist_list,
        "is_significant_night_owl": is_significant,
        "tool_note": (
            "Có xu hướng nghe đêm rõ nét, có thể tạo fact."
            if is_significant
            else "Số lượt nghe đêm không nhiều, nên ưu tiên công cụ khác nếu cần thêm fact nổi bật."
        ),
    }

def query_marathon_sessions(user, start_dt, end_dt, max_gap_minutes: int = 20) -> dict:
    """
    Truy vet phien nghe nhac lien tuc dai nhat (Marathon Listening Session).
    Hai luot nghe cach nhau <= max_gap_minutes duoc tinh la cung mot session.
    """
    records = list(
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
        )
        .select_related('track')
        .order_by('played_at')
        .values_list('played_at', 'track__duration_ms', 'track__name')
    )

    if not records:
        return {"tool_name": "query_marathon_sessions", "has_data": False}

    max_session_count = 0
    max_session_duration_sec = 0
    max_session_start = None
    max_session_end = None

    current_count = 1
    current_start = records[0][0]
    current_duration_sec = (records[0][1] or 180000) / 1000

    for i in range(1, len(records)):
        prev_time = records[i - 1][0]
        curr_time = records[i][0]
        gap_sec = (curr_time - prev_time).total_seconds()

        if gap_sec <= max_gap_minutes * 60:
            current_count += 1
            current_duration_sec += (records[i][1] or 180000) / 1000
        else:
            if current_count > max_session_count:
                max_session_count = current_count
                max_session_duration_sec = current_duration_sec
                max_session_start = current_start
                max_session_end = prev_time

            current_count = 1
            current_start = curr_time
            current_duration_sec = (records[i][1] or 180000) / 1000

    if current_count > max_session_count:
        max_session_count = current_count
        max_session_duration_sec = current_duration_sec
        max_session_start = current_start
        max_session_end = records[-1][0]

    hours = round(max_session_duration_sec / 3600, 1)

    local_start = timezone.localtime(max_session_start) if max_session_start else None
    local_end = timezone.localtime(max_session_end) if max_session_end else None

    return {
        "tool_name": "query_marathon_sessions",
        "has_data": max_session_count >= 5,
        "max_tracks_count": max_session_count,
        "duration_hours": hours,
        "session_date": local_start.strftime('%d/%m/%Y') if local_start else "Trong kỳ",
        "time_window": (
            f"{local_start.strftime('%H:%M')} - {local_end.strftime('%H:%M')}"
            if local_start and local_end else ""
        ),
    }

def query_artist_dominance(user, start_dt, end_dt) -> dict:
    """
    Do luong muc do trung thanh va chiem song cua nghe si dung dau (Artist Loyalty).
    """
    total_plays = ListeningHistory.objects.filter(
        user=user,
        played_at__range=(start_dt, end_dt),
    ).count()

    if total_plays == 0:
        return {"tool_name": "query_artist_dominance", "has_data": False}

    top_artists = (
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
        )
        .values('track__artists__name')
        .annotate(play_count=Count('id'))
        .exclude(track__artists__name__isnull=True)
        .order_by('-play_count')[:3]
    )

    if not top_artists:
        return {"tool_name": "query_artist_dominance", "has_data": False}

    top_1 = top_artists[0]
    top_1_name = top_1['track__artists__name']
    top_1_plays = top_1['play_count']
    percentage = round((top_1_plays / total_plays) * 100, 1)

    return {
        "tool_name": "query_artist_dominance",
        "has_data": True,
        "top_artist_name": top_1_name,
        "top_artist_plays": top_1_plays,
        "total_period_plays": total_plays,
        "dominance_percentage": percentage,
        "is_highly_loyal": percentage >= 25.0,
    }

def query_tempo_or_energy_contrast(user, start_dt, end_dt) -> dict:
    """
    Kiem tra su bien doi cam xuc hoac nhịp dieu dot ngot giua hai bai hat nghe ke tiep.
    Vi du: Chuyen ngay tu mot ban ballad nhe nhang sang mot ban EDM 150 BPM.
    """
    records = list(
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
        )
        .select_related('track')
        .filter(track__features_synced=True)
        .order_by('played_at')[:80]
    )

    if len(records) < 2:
        return {"tool_name": "query_tempo_or_energy_contrast", "has_data": False}

    max_energy_jump = 0.0
    best_pair = None

    for i in range(1, len(records)):
        t1 = records[i - 1].track
        t2 = records[i].track
        if t1.id == t2.id:
            continue

        energy_diff = abs(t1.energy - t2.energy)
        if energy_diff > max_energy_jump:
            max_energy_jump = energy_diff
            best_pair = (records[i - 1], records[i], energy_diff)

    if best_pair and max_energy_jump >= 0.40:
        rec1, rec2, diff = best_pair
        return {
            "tool_name": "query_tempo_or_energy_contrast",
            "has_data": True,
            "energy_contrast": round(diff * 100, 1),
            "track_before": f"{rec1.track.name} (Năng lượng: {round(rec1.track.energy * 100)}%)",
            "track_after": f"{rec2.track.name} (Năng lượng: {round(rec2.track.energy * 100)}%)",
            "played_time": rec2.played_at.strftime('%H:%M ngày %d/%m/%Y'),
        }

    return {"tool_name": "query_tempo_or_energy_contrast", "has_data": False}
