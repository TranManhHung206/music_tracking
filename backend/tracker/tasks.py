"""
Celery Tasks cho app tracker.
Quan ly tac vu cao lich su nghe nhac bat dong bo va dinh ky Celery Beat.
"""

import logging
from celery import shared_task
from django.contrib.auth.models import User
from users.models import SpotifyProfile
from tracker.services.ingestion import sync_user_recently_played_pipeline

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_user_recently_played_task(self, user_id: int):
    """Celery task chay bat dong bo cho tung user, xu ly retry va rate limit."""
    try:
        user = User.objects.get(id=user_id)
        result = sync_user_recently_played_pipeline(user)
        logger.info(f"Sync complete for user_id={user_id}: {result}")
        return result
    except User.DoesNotExist:
        logger.warning(f"User id={user_id} khong ton tai.")
        return {"status": "error", "message": "User not found"}
    except RuntimeError as exc:
        err_msg = str(exc)
        if err_msg.startswith("SPOTIFY_RATE_LIMIT:"):
            try:
                retry_after = int(err_msg.split(":")[1])
            except (IndexError, ValueError):
                retry_after = 60
            logger.warning(f"Spotify 429 Rate Limit for user_id={user_id}. Backing off for {retry_after}s.")
            raise self.retry(exc=exc, countdown=retry_after)
        raise self.retry(exc=exc, countdown=60)
    except Exception as exc:
        logger.error(f"Loi sync cho user_id={user_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)

@shared_task
def scheduled_scrobble_all_users():
    """Task dinh ky Celery Beat: dispatcher tao sub-task cho tung user dang hoat dong."""
    active_user_ids = list(
        SpotifyProfile.objects.filter(is_sync_active=True).values_list('user_id', flat=True)
    )
    logger.info(f"Dispatching scheduled scrobble for {len(active_user_ids)} active users.")
    for user_id in active_user_ids:
        sync_user_recently_played_task.delay(user_id)
    return {"dispatched_users_count": len(active_user_ids)}
