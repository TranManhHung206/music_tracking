"""
Redis & In-Memory Caching Service
Cung cap lop cache hieu nang cao (<1.5s) va co che du phong an toan (Graceful Fallback).
"""

import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

def build_analytics_cache_key(user_id: int, metric_name: str, range_key: str) -> str:
    """Tao cache key chuan: analytics:{user_id}:{metric_name}:{range_key}."""
    return f"analytics:{user_id}:{metric_name}:{range_key}"

def get_or_set_cached_metric(cache_key: str, ttl: int, compute_fn):
    """
    Lay ket qua tu Cache. Neu cache miss hoac Redis gap su co,
    thuc thi compute_fn truc tiep tu DB va cache lai ma khong lam crash he thong.
    """
    try:
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
    except Exception as e:
        logger.warning(f"Cache get failed for {cache_key}: {e}. Falling back to DB compute.")

    # Tinh toan truc tiep tu DB
    data = compute_fn()

    # Neu du lieu rong hoac chua co luot nghe nao, chi cache 5 giay de tranh luu cache cu
    effective_ttl = ttl
    is_empty = False
    if isinstance(data, dict):
        if data.get('total_plays') == 0:
            is_empty = True
        elif 'tracks' in data and len(data['tracks']) == 0:
            is_empty = True
        elif 'artists' in data and len(data['artists']) == 0:
            is_empty = True
        elif 'genres' in data and len(data['genres']) == 0:
            is_empty = True
        elif 'timeline' in data and len(data['timeline']) == 0:
            is_empty = True
    elif isinstance(data, list) and len(data) == 0:
        is_empty = True

    if is_empty:
        effective_ttl = 5

    try:
        cache.set(cache_key, data, timeout=effective_ttl)
    except Exception as e:
        logger.warning(f"Cache set failed for {cache_key}: {e}.")

    return data

def invalidate_user_analytics_cache(user_id: int):
    """Xoa toan bo cache thong ke cua user khi co du lieu moi hoac dang nhap lai."""
    try:
        # 1. Neu la Redis hoac cache backend co ho tro delete_pattern
        if hasattr(cache, 'delete_pattern'):
            try:
                cache.delete_pattern(f"analytics:{user_id}:*")
                return
            except Exception:
                pass

        # 2. Neu la LocMemCache (chay local dev) - Xoa truc tiep tu internal dict
        if hasattr(cache, '_cache'):
            try:
                prefix = f"analytics:{user_id}:"
                raw_keys = list(cache._cache.keys())
                for k in raw_keys:
                    if prefix in str(k):
                        cache._cache.pop(k, None)
                        if hasattr(cache, '_expire_info'):
                            cache._expire_info.pop(k, None)
            except Exception:
                pass

        # 3. Quet va xoa toan bo to hop key pho bien
        metrics = ['summary', 'top_tracks', 'top_artists', 'radar', 'heatmap', 'bar_chart_race', 'genres']
        ranges = ['7d', '30d', '1y']
        limits = [5, 10, 20, 50]

        for metric in metrics:
            for r in ranges:
                cache.delete(build_analytics_cache_key(user_id, metric, r))
                for lim in limits:
                    cache.delete(f"{build_analytics_cache_key(user_id, metric, r)}:{lim}")

        # 4. Neu chay LocMemCache local va khong co delete_pattern, don dep sach cache de tranh sai lech so lieu
        if not hasattr(cache, 'delete_pattern'):
            try:
                cache.clear()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Invalidate cache failed for user {user_id}: {e}.")
