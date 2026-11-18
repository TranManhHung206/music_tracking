"""
Time Filter Service cho app analytics.
Xu ly cac khoang thoi gian loc 7d, 30d, 1y va cac chu ky lich co dinh (Tuan / Thang / Nam).
"""

import calendar
import hashlib
from datetime import datetime, time, timedelta, date
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from tracker.models import ListeningHistory

def get_time_range_bounds(time_range: str = '30d', start_date_str: str = None, end_date_str: str = None) -> tuple[datetime, datetime, str]:
    """
    Xac dinh thoi diem bat dau va ket thuc theo bo loc thoi gian.
    Tra ve (start_dt, end_dt, normalized_range_key).
    """
    now = timezone.now()
    range_key = (time_range or '30d').lower()

    if start_date_str and end_date_str:
        try:
            s_date = datetime.strptime(start_date_str.strip(), '%Y-%m-%d').date()
            e_date = datetime.strptime(end_date_str.strip(), '%Y-%m-%d').date()
            start_dt = timezone.make_aware(datetime.combine(s_date, time.min))
            end_dt = timezone.make_aware(datetime.combine(e_date, time.max))
            range_key = f"period_{s_date.isoformat()}_{e_date.isoformat()}"
            return start_dt, end_dt, range_key
        except Exception:
            pass

    today = timezone.localdate(now)
    if range_key == 'week':
        # Tuan hien tai: Tu 00:00 Thu 2 den 23:59 Chu Nhat
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        start_dt = timezone.make_aware(datetime.combine(monday, time.min))
        end_dt = timezone.make_aware(datetime.combine(sunday, time.max))
        range_key = f"period_{monday.isoformat()}_{sunday.isoformat()}"
    elif range_key == 'month':
        # Thang hien tai: Tu ngay 1 den ngay cuoi thang
        first_day = date(today.year, today.month, 1)
        last_day_num = calendar.monthrange(today.year, today.month)[1]
        last_day = date(today.year, today.month, last_day_num)
        start_dt = timezone.make_aware(datetime.combine(first_day, time.min))
        end_dt = timezone.make_aware(datetime.combine(last_day, time.max))
        range_key = f"period_{first_day.isoformat()}_{last_day.isoformat()}"
    elif range_key == 'year':
        # Nam hien tai: Tu 01/01 den 31/12
        first_day = date(today.year, 1, 1)
        last_day = date(today.year, 12, 31)
        start_dt = timezone.make_aware(datetime.combine(first_day, time.min))
        end_dt = timezone.make_aware(datetime.combine(last_day, time.max))
        range_key = f"period_{first_day.isoformat()}_{last_day.isoformat()}"
    elif range_key == '7d':
        start_dt = now - timedelta(days=7)
        end_dt = now
    elif range_key == '1y':
        start_dt = now - timedelta(days=365)
        end_dt = now
    else:
        start_dt = now - timedelta(days=30)
        end_dt = now
        range_key = '30d'

    return start_dt, end_dt, range_key

def get_cache_ttl_for_range(range_key: str) -> int:
    """Xac dinh thoi gian song TTL (giay) cho cache theo pham vi thoi gian."""
    if range_key.startswith('period_'):
        # Neu khoang thoi gian da ket thuc trong qua khu, cache bat bien 30 ngay
        parts = range_key.split('_')
        if len(parts) >= 3:
            try:
                end_date = datetime.strptime(parts[2], '%Y-%m-%d').date()
                if end_date < timezone.localdate():
                    return 86400 * 30
            except Exception:
                pass
        return 60 # Ky hien tai: 60 giay de dong bo lien tuc voi luot nghe moi

    if range_key.startswith('7d'):
        return 900
    elif range_key.startswith('30d'):
        return 1800
    elif range_key.startswith('1y') or range_key.startswith('custom'):
        return 86400
    return 1800

def get_calendar_periods(user, period_type: str = 'week', limit: int = 12) -> list[dict]:
    """
    Sinh danh sach cac ky thoi gian Tu Hien Tai Ve Qua Khu.
    Tuyet doi khong hien thi tuong lai.
    Moi ky kem so luot nghe thuc te cua nguoi dung (1 truy van TruncDate gom nhom).
    """
    now = timezone.now()
    user_tz = timezone.get_current_timezone()
    today = timezone.localdate(now)
    p_type = (period_type or 'week').lower()
    window_defs: list[tuple[str, str, date, date, bool]] = []

    if p_type == 'week':
        curr_monday = today - timedelta(days=today.weekday())
        for i in range(limit):
            mon = curr_monday - timedelta(weeks=i)
            sun = mon + timedelta(days=6)
            is_curr = (i == 0)
            iso_year, iso_week, _ = mon.isocalendar()

            if is_curr:
                label = "Tuần này"
            elif iso_year != today.year:
                label = f"Tuần {iso_week} ({iso_year})"
            else:
                label = f"Tuần {iso_week}"

            window_defs.append((f"{iso_year}-W{iso_week:02d}", label, mon, sun, is_curr))

    elif p_type == 'month':
        curr_y, curr_m = today.year, today.month
        for i in range(limit):
            total_m = (curr_y * 12 + curr_m - 1) - i
            y = total_m // 12
            m = total_m % 12 + 1
            first_day = date(y, m, 1)
            last_day = date(y, m, calendar.monthrange(y, m)[1])
            is_curr = (i == 0)
            window_defs.append((f"{y}-{m:02d}", f"Tháng {m:02d}/{y}", first_day, last_day, is_curr))

    elif p_type == 'year':
        year_limit = min(limit, 5)
        for i in range(year_limit):
            y = today.year - i
            first_day = date(y, 1, 1)
            last_day = date(y, 12, 31)
            is_curr = (i == 0)
            window_defs.append((str(y), f"Năm {y}", first_day, last_day, is_curr))

    if not window_defs:
        return []

    min_start = min(w[2] for w in window_defs)
    max_end = max(w[3] for w in window_defs)
    min_dt = timezone.make_aware(datetime.combine(min_start, time.min))
    max_dt = timezone.make_aware(datetime.combine(max_end, time.max))

    daily_rows = (
        ListeningHistory.objects.filter(user=user, played_at__range=(min_dt, max_dt))
        .annotate(play_date=TruncDate('played_at', tzinfo=user_tz))
        .values('play_date')
        .annotate(cnt=Count('id'))
    )
    daily_map = {row['play_date']: row['cnt'] for row in daily_rows if row['play_date'] is not None}

    periods = []
    for key, label, s_date, e_date, is_curr in window_defs:
        play_count = sum(cnt for d, cnt in daily_map.items() if s_date <= d <= e_date)
        periods.append({
            "key": key,
            "label": label,
            "start_date": s_date.strftime('%Y-%m-%d'),
            "end_date": e_date.strftime('%Y-%m-%d'),
            "is_current": is_curr,
            "play_count": play_count,
        })
    return periods
