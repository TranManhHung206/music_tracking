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

    try:
        cache.set(cache_key, data, timeout=ttl)
    except Exception as e:
        logger.warning(f"Cache set failed for {cache_key}: {e}.")

    return data

def invalidate_user_analytics_cache(user_id: int):
    """Xoa cache thong ke cua user khi co bai hat moi duoc scrobble."""
    try:
        # Neu dung RedisCache ho tro delete_pattern
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern(f"analytics:{user_id}:*")
        else:
            # Fallback xoa cac keys pho bien
            for metric in ['summary', 'top_tracks', 'top_artists', 'radar', 'heatmap', 'bar_chart_race']:
                for r in ['7d', '30d', '1y']:
                    cache.delete(build_analytics_cache_key(user_id, metric, r))
    except Exception as e:
        logger.warning(f"Invalidate cache failed for user {user_id}: {e}.")
