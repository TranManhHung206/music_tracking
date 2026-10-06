"""
Ingestion & Scrobbling Service
Cung cap logic thu thap Recently Played tu Spotify API, deduplication 2 tang, va dong bo Audio Features.
"""

from datetime import datetime
import requests
from django.utils import timezone
from django.db import transaction

from users.services.spotify_auth import get_valid_access_token
from tracker.models import Artist, Album, Track, ListeningHistory

SPOTIFY_RECENTLY_PLAYED_URL = "https://api.spotify.com/v1/me/player/recently-played"
SPOTIFY_AUDIO_FEATURES_URL = "https://api.spotify.com/v1/audio-features"

def parse_iso_datetime(iso_str: str) -> datetime:
    """Chuyen doi chuoi ISO 8601 tu Spotify ve datetime object co timezone."""
    clean_str = iso_str.replace("Z", "+00:00")
    return datetime.fromisoformat(clean_str)

def fetch_recently_played_from_api(access_token: str, after_ms: int = None, limit: int = 50) -> dict:
    """Goi API Spotify de lay danh sach 50 bai hat vua nghe gan nhat."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"limit": min(limit, 50)}
    if after_ms:
        params["after"] = after_ms

    response = requests.get(SPOTIFY_RECENTLY_PLAYED_URL, headers=headers, params=params, timeout=10)
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise RuntimeError(f"SPOTIFY_RATE_LIMIT:{retry_after}")
    if response.status_code != 200:
        raise ValueError(f"Spotify recently-played request failed ({response.status_code}): {response.text}")

    return response.json()

def fetch_audio_features_from_api(access_token: str, track_spotify_ids: list[str]) -> list[dict]:
    """Goi API Spotify de lay Audio Features cho danh sach track IDs (toi da 100 tracks/request)."""
    if not track_spotify_ids:
        return []

    headers = {"Authorization": f"Bearer {access_token}"}
    ids_param = ",".join(track_spotify_ids[:100])
    response = requests.get(SPOTIFY_AUDIO_FEATURES_URL, headers=headers, params={"ids": ids_param}, timeout=10)
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise RuntimeError(f"SPOTIFY_RATE_LIMIT:{retry_after}")
    if response.status_code != 200:
        return []

    data = response.json()
    return [item for item in data.get("audio_features", []) if item is not None]

def ingest_recently_played_payload(user, payload: dict) -> dict:
    """Xu ly du lieu payload tu Spotify: phan tach thuc the, deduplicate va bulk_create vao DB."""
    items = payload.get("items", [])
    if not items:
        return {"scrobbled_count": 0, "tracks_processed": 0}

    # Tuan 1: Deduplication trong Memory theo cap (user_id, played_at)
    seen_events = set()
    unique_items = []
    for item in items:
        played_at_str = item.get("played_at")
        track_data = item.get("track")
        if not played_at_str or not track_data or not track_data.get("id"):
            continue

        played_at_dt = parse_iso_datetime(played_at_str)
        event_key = (user.id, played_at_dt)
        if event_key not in seen_events:
            seen_events.add(event_key)
            unique_items.append((played_at_dt, item))

    history_to_create = []
    tracks_to_feature_sync = []

    with transaction.atomic():
        for played_at_dt, item in unique_items:
            track_dict = item.get("track", {})
            album_dict = track_dict.get("album", {})
            artists_list = track_dict.get("artists", [])
            context = item.get("context")
            context_type = context.get("type") if context else None

            # 1. Xu ly Artists
            artist_instances = []
            for art_data in artists_list:
                art_id = art_data.get("id")
                art_name = art_data.get("name") or "Unknown Artist"
                if not art_id:
                    continue
                artist_obj, _ = Artist.objects.get_or_create(
                    spotify_id=art_id,
                    defaults={"name": art_name}
                )
                artist_instances.append(artist_obj)

            # 2. Xu ly Album
            album_obj = None
            if album_dict and album_dict.get("id"):
                alb_id = album_dict.get("id")
                alb_name = album_dict.get("name") or "Unknown Album"
                release_date = album_dict.get("release_date", "")
                images = album_dict.get("images", [])
                image_url = images[0].get("url") if images else None

                album_obj, _ = Album.objects.get_or_create(
                    spotify_id=alb_id,
                    defaults={
                        "name": alb_name,
                        "release_date": release_date,
                        "image_url": image_url,
                    }
                )
                if artist_instances:
                    album_obj.artists.add(*artist_instances)

            # 3. Xu ly Track
            track_id = track_dict.get("id")
            track_name = track_dict.get("name") or "Unknown Track"
            duration_ms = track_dict.get("duration_ms", 0)

            track_obj, created = Track.objects.get_or_create(
                spotify_id=track_id,
                defaults={
                    "name": track_name,
                    "duration_ms": duration_ms,
                    "album": album_obj,
                }
            )
            if created or not track_obj.features_synced:
                tracks_to_feature_sync.append(track_obj)

            if artist_instances:
                track_obj.artists.add(*artist_instances)

            # 4. Khoi tao ban ghi ListeningHistory
            history_to_create.append(
                ListeningHistory(
                    user=user,
                    track=track_obj,
                    played_at=played_at_dt,
                    context_type=context_type,
                    raw_spotify_data={
                        "track_name": track_name,
                        "popularity": track_dict.get("popularity"),
                    }
                )
            )

        # Tuan 2: Ràng buộc Database voi bulk_create ignore_conflicts=True
        created_records = ListeningHistory.objects.bulk_create(
            history_to_create,
            ignore_conflicts=True
        )

    return {
        "scrobbled_count": len(created_records),
        "tracks_to_feature_sync": [t.spotify_id for t in tracks_to_feature_sync]
    }

def sync_audio_features_for_unsynced_tracks(access_token: str, limit: int = 50) -> int:
    """Dong bo cac chi so Audio Features (valence, energy, danceability, v.v.) cho cac bai hat chua co."""
    unsynced_tracks = list(Track.objects.filter(features_synced=False)[:limit])
    if not unsynced_tracks:
        return 0

    track_id_map = {t.spotify_id: t for t in unsynced_tracks}
    features_list = fetch_audio_features_from_api(access_token, list(track_id_map.keys()))

    updated_count = 0
    for feat in features_list:
        sp_id = feat.get("id")
        if sp_id in track_id_map:
            t = track_id_map[sp_id]
            t.danceability = float(feat.get("danceability", 0.0))
            t.energy = float(feat.get("energy", 0.0))
            t.valence = float(feat.get("valence", 0.0))
            t.acousticness = float(feat.get("acousticness", 0.0))
            t.tempo = float(feat.get("tempo", 0.0))
            t.features_synced = True
            t.save(update_fields=["danceability", "energy", "valence", "acousticness", "tempo", "features_synced"])
            updated_count += 1

    return updated_count

def sync_user_recently_played_pipeline(user) -> dict:
    """Pipeline hoan chinh: lay token hop le, tinh cursor, fetch Spotify, ingest va sync features."""
    profile = getattr(user, 'spotify_profile', None)
    if not profile or not profile.is_sync_active:
        return {"status": "skipped", "reason": "Sync inactive hoac chua lien ket Spotify profile."}

    access_token = get_valid_access_token(profile)

    # Tinh toan cursor timestamp milliseconds de toi uu payload
    last_played = ListeningHistory.objects.filter(user=user).order_by('-played_at').values_list('played_at', flat=True).first()
    after_ms = int(last_played.timestamp() * 1000) if last_played else None

    # Fetch va Ingest
    payload = fetch_recently_played_from_api(access_token, after_ms=after_ms, limit=50)
    ingest_result = ingest_recently_played_payload(user, payload)

    # Dong bo Audio Features
    features_synced_count = sync_audio_features_for_unsynced_tracks(access_token, limit=50)

    # Xoa cache thong ke cu khi co du lieu scrobble moi
    scrobbled_count = ingest_result.get("scrobbled_count", 0)
    if scrobbled_count > 0:
        try:
            from analytics.services.caching import invalidate_user_analytics_cache
            invalidate_user_analytics_cache(user.id)
        except Exception:
            pass

    # Cap nhat moc thoi gian sync
    profile.last_synced_at = timezone.now()
    profile.save(update_fields=["last_synced_at", "updated_at"])

    return {
        "status": "success",
        "scrobbled_count": scrobbled_count,
        "features_synced_count": features_synced_count,
        "last_synced_at": profile.last_synced_at.isoformat()
    }
