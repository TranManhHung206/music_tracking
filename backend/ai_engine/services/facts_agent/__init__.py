"""
Package facts_agent cho ung dung ai_engine.
Cung cap ham get_or_generate_music_facts tich hop Caching va Agentic AI (Groq + Harness).
"""

import re
from datetime import datetime, date, time, timedelta
import calendar
from django.utils import timezone
from django.core.cache import cache

from .agent import run_music_facts_agent
from .harness import generate_heuristic_facts

def parse_period_to_bounds(period_key: str = 'week') -> tuple[datetime, datetime, str]:
    """
    Chuyen doi period_key thanh cap mox thoi gian (start_dt, end_dt) va nhan hien thi.
    Ho tro:
    - 2026-W42 (ISO Week)
    - 2026-10 (Thang)
    - 2026 (Nam)
    - week, month, year, 7d, 30d
    """
    now = timezone.now()
    today = now.date()
    p_str = (period_key or 'week').strip()

    # 1. Kiem tra ISO Week: YYYY-Www
    week_match = re.match(r'^(\d{4})-W(\d{1,2})$', p_str, re.IGNORECASE)
    if week_match:
        iso_year = int(week_match.group(1))
        iso_week = int(week_match.group(2))
        try:
            monday = date.fromisocalendar(iso_year, iso_week, 1)
            sunday = date.fromisocalendar(iso_year, iso_week, 7)
            start_dt = timezone.make_aware(datetime.combine(monday, time.min))
            end_dt = timezone.make_aware(datetime.combine(sunday, time.max))
            return start_dt, end_dt, f"Tuần {iso_week}/{iso_year}"
        except Exception:
            pass

    # 2. Kiem tra Thang: YYYY-MM
    month_match = re.match(r'^(\d{4})-(\d{1,2})$', p_str)
    if month_match:
        year = int(month_match.group(1))
        month = int(month_match.group(2))
        try:
            first_day = date(year, month, 1)
            last_day_num = calendar.monthrange(year, month)[1]
            last_day = date(year, month, last_day_num)
            start_dt = timezone.make_aware(datetime.combine(first_day, time.min))
            end_dt = timezone.make_aware(datetime.combine(last_day, time.max))
            return start_dt, end_dt, f"Tháng {month:02d}/{year}"
        except Exception:
            pass

    # 3. Kiem tra Nam: YYYY
    year_match = re.match(r'^(\d{4})$', p_str)
    if year_match:
        year = int(year_match.group(1))
        try:
            first_day = date(year, 1, 1)
            last_day = date(year, 12, 31)
            start_dt = timezone.make_aware(datetime.combine(first_day, time.min))
            end_dt = timezone.make_aware(datetime.combine(last_day, time.max))
            return start_dt, end_dt, f"Năm {year}"
        except Exception:
            pass

    # 4. Cac gia tri mac dinh tuong doi
    if p_str in ['week', '7d']:
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        start_dt = timezone.make_aware(datetime.combine(monday, time.min))
        end_dt = timezone.make_aware(datetime.combine(sunday, time.max))
        return start_dt, end_dt, "Tuần này"
    elif p_str in ['month', '30d']:
        first_day = date(today.year, today.month, 1)
        last_day_num = calendar.monthrange(today.year, today.month)[1]
        last_day = date(today.year, today.month, last_day_num)
        start_dt = timezone.make_aware(datetime.combine(first_day, time.min))
        end_dt = timezone.make_aware(datetime.combine(last_day, time.max))
        return start_dt, end_dt, "Tháng này"
    elif p_str in ['year', '1y']:
        first_day = date(today.year, 1, 1)
        last_day = date(today.year, 12, 31)
        start_dt = timezone.make_aware(datetime.combine(first_day, time.min))
        end_dt = timezone.make_aware(datetime.combine(last_day, time.max))
        return start_dt, end_dt, "Năm nay"

    # Mac dinh fallback 30 ngay gan nhat
    start_dt = now - timedelta(days=30)
    end_dt = now
    return start_dt, end_dt, "Kỳ phân tích gần đây"

def get_or_generate_music_facts(
    user,
    period_key: str = 'week',
    force_refresh: bool = False,
    allow_ai_generation: bool = False,
) -> dict:
    """
    Lay du lieu Music Facts tu Cache hoac kich hoat Groq Agent sinh moi.
    - Neu allow_ai_generation=False (duyet xem thong thuong): Chi tra ve du lieu Cache
      hoac tinh toan nhanh qua Heuristic Engine (0 token AI).
    - Neu allow_ai_generation=True (nguoi dung bam nut thu cong): Kich hoat ReAct Agent voi cooldown 15s.
    """
    clean_period = (period_key or 'week').strip()
    cache_key = f"user_music_facts:{user.id}:{clean_period}"
    start_dt, end_dt, period_label = parse_period_to_bounds(clean_period)

    # 1. Neu khong yeu cau refresh, uu tien doc tu Cache
    if not force_refresh:
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

    # 2. Neu nguoi dung khong chu dong bam kich hoat AI (chi duyet web binh thuong)
    if not allow_ai_generation:
        # Tra ve facts tinh toan nhanh tu Heuristic Engine, 0 token AI
        heuristic_facts = generate_heuristic_facts(user, start_dt, end_dt)
        response_payload = {
            "facts": heuristic_facts,
            "agent_meta": {
                "agent_name": "Aura Music Detective",
                "provider_used": "db-analytics-preview",
                "model_name": "db-analytics-heuristic",
                "iterations_used": 0,
                "tools_called": ["direct_db_queries"],
                "is_fallback": True,
            },
            "period_key": clean_period,
            "period_label": period_label,
        }
        # Cache ngan 1 gio cho preview
        cache.set(cache_key, response_payload, timeout=3600)
        return response_payload

    # 3. Khi nguoi dung bam nut kich hoat AI thu cong: Kiem tra Anti-Spam Cooldown 15s
    cooldown_key = f"user_facts_cooldown:{user.id}"
    if cache.get(cooldown_key):
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
    cache.set(cooldown_key, True, timeout=15)

    # Kich hoat Agent voi kien truc du phong 3 tang
    agent_result = run_music_facts_agent(user, start_dt, end_dt, period_label=period_label)

    response_payload = {
        "facts": agent_result.get("facts", []),
        "agent_meta": agent_result.get("agent_meta", {}),
        "period_key": clean_period,
        "period_label": period_label,
    }

    # Luu vao cache voi TTL 6 gio
    cache.set(cache_key, response_payload, timeout=21600)
    return response_payload

__all__ = [
    'get_or_generate_music_facts',
    'parse_period_to_bounds',
    'run_music_facts_agent',
    'generate_heuristic_facts',
]
