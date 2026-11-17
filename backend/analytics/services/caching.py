"""
Redis & In-Memory Caching Service
Cung cap lop cache hieu nang cao (<1.5s), co lap tung user bang cache version
va co che du phong an toan (Graceful Fallback).
"""

import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Danh sach cac nhom metric duoc bao phu boi co che versioned invalidation (bao gom ca key :limit)
TRACKED_ANALYTICS_METRICS = (
    'summary',
    'top_tracks',
    'top_artists',
    'top_albums',
    'radar',
    'heatmap',
    'bar_chart_race',
    'weekly_comparison',
    'genres',
)

VERSION_KEY_TTL = 86400 * 30


def _version_cache_key(user_id: int) -> str:
    return f"analytics_ver:{user_id}"


def get_user_cache_version(user_id: int) -> int:
    """Lay phien ban cache hien tai cua user (mac dinh 1)."""
    ver_key = _version_cache_key(user_id)
    try:
        version = cache.get(ver_key)
        if version is None:
            cache.set(ver_key, 1, timeout=VERSION_KEY_TTL)
            return 1
        return int(version)
    except Exception as e:
        logger.warning(f"Cache version get failed for user {user_id}: {e}.")
        return 1


def build_analytics_cache_key(user_id: int, metric_name: str, range_key: str, limit: int | None = None) -> str:
    """Tao cache key co lap theo user version: analytics:v{ver}:{user_id}:{metric_name}:{range_key}[:limit]."""
    version = get_user_cache_version(user_id)
    base_key = f"analytics:v{version}:{user_id}:{metric_name}:{range_key}"
    if limit is not None:
        return f"{base_key}:{limit}"
    return base_key


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
        elif 'albums' in data and len(data['albums']) == 0:
            is_empty = True
        elif 'days' in data and len(data['days']) == 0:
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
    """
    Vo hieu hoa toan bo cache thong ke cua rieng user_id bang cach tang cache version.
    Khong su dung cache.clear() de tranh xoa nham cache cua user khac va AI/cooldown keys.
    """
    ver_key = _version_cache_key(user_id)
    try:
        try:
            cache.incr(ver_key)
            return
        except ValueError:
            # Key chua ton tai trong cache backend -> khoi tao o version 2
            cache.set(ver_key, 2, timeout=VERSION_KEY_TTL)
            return
        except Exception:
            pass

        current = cache.get(ver_key)
        next_ver = (int(current) + 1) if current is not None else 2
        cache.set(ver_key, next_ver, timeout=VERSION_KEY_TTL)
    except Exception as e:
        logger.warning(f"Invalidate cache failed for user {user_id}: {e}.")
