"""
Time Filter Service cho app analytics.
Xu ly cac khoang thoi gian loc 7d, 30d, 1y va custom range chuan ISO.
"""

from datetime import datetime, time, timedelta
from django.utils import timezone
import hashlib

def get_time_range_bounds(time_range: str = '30d', start_date_str: str = None, end_date_str: str = None) -> tuple[datetime, datetime, str]:
    """
    Xac dinh thoi diem bat dau va ket thuc theo bo loc thoi gian.
    Tra ve (start_dt, end_dt, normalized_range_key).
    """
    now = timezone.now()
    range_key = (time_range or '30d').lower()

    if range_key == '7d':
        start_dt = now - timedelta(days=7)
        end_dt = now
    elif range_key == '1y':
        start_dt = now - timedelta(days=365)
        end_dt = now
    elif range_key == 'custom' and start_date_str and end_date_str:
        try:
            s_date = datetime.strptime(start_date_str.strip(), '%Y-%m-%d').date()
            e_date = datetime.strptime(end_date_str.strip(), '%Y-%m-%d').date()
            start_dt = timezone.make_aware(datetime.combine(s_date, time.min))
            end_dt = timezone.make_aware(datetime.combine(e_date, time.max))
            # Tao hash key ngan cho custom date
            hash_suffix = hashlib.md5(f"{start_date_str}_{end_date_str}".encode('utf-8')).hexdigest()[:8]
            range_key = f"custom_{hash_suffix}"
        except Exception:
            # Fallback ve 30d neu tham so khong hop le
            start_dt = now - timedelta(days=30)
            end_dt = now
            range_key = '30d'
    else: # Mac dinh 30d
        start_dt = now - timedelta(days=30)
        end_dt = now
        range_key = '30d'

    return start_dt, end_dt, range_key

def get_cache_ttl_for_range(range_key: str) -> int:
    """Xac dinh thoi gian song TTL (giay) cho cache theo pham vi thoi gian."""
    if range_key.startswith('7d'):
        return 900 # 15 phut
    elif range_key.startswith('30d'):
        return 1800 # 30 phut
    elif range_key.startswith('1y') or range_key.startswith('custom'):
        return 86400 # 24 gio
    return 1800
