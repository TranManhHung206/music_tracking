"""
Ingestion & Scrobbling Service
Cung cap logic thu thap Recently Played tu Spotify API, deduplication 2 tang, va dong bo Audio Features.
"""

from datetime import datetime, timedelta
import time
import requests
from django.utils import timezone
from django.db import transaction

from users.services.spotify_auth import get_valid_access_token, get_spotify_session
from tracker.models import Artist, Album, Track, ListeningHistory

SPOTIFY_RECENTLY_PLAYED_URL = "https://api.spotify.com/v1/me/player/recently-played"
SPOTIFY_AUDIO_FEATURES_URL = "https://api.spotify.com/v1/audio-features"
SPOTIFY_ARTIST_URL = "https://api.spotify.com/v1/artists"

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

    session = get_spotify_session()
    response = session.get(SPOTIFY_RECENTLY_PLAYED_URL, headers=headers, params=params, timeout=(10, 20))
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
    session = get_spotify_session()
    response = session.get(SPOTIFY_AUDIO_FEATURES_URL, headers=headers, params={"ids": ids_param}, timeout=(10, 20))
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "60")
        raise RuntimeError(f"SPOTIFY_RATE_LIMIT:{retry_after}")
    if response.status_code != 200:
        return []

    data = response.json()
    return [item for item in data.get("audio_features", []) if item is not None]

def fetch_artist_from_spotify_api(access_token: str, artist_spotify_id: str, profile=None) -> dict | None:
    """Goi API Spotify de lay thong tin chi tiet mot nghe si qua ID rieng."""
    if not artist_spotify_id:
        return None
    url = f"{SPOTIFY_ARTIST_URL}/{artist_spotify_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    session = get_spotify_session()
    try:
        response = session.get(url, headers=headers, timeout=(10, 15))
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "5"))
            time.sleep(retry_after)
            response = session.get(url, headers=headers, timeout=(10, 15))
        elif response.status_code == 401 and profile:
            new_token = get_valid_access_token(profile)
            headers = {"Authorization": f"Bearer {new_token}"}
            response = session.get(url, headers=headers, timeout=(10, 15))
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def sync_artist_images_from_spotify(user=None, limit: int = None, force: bool = False) -> dict:
    """Dong bo avatar chinh chu tu Spotify Web API cho cac nghe si theo spotify_id."""
    from users.models import User

    if user is None:
        user = User.objects.filter(spotify_profile__isnull=False, spotify_profile__is_sync_active=True).first()
        if not user:
            user = User.objects.filter(spotify_profile__isnull=False).first()

    if not user or not hasattr(user, 'spotify_profile') or not user.spotify_profile:
        return {"total_checked": 0, "updated_count": 0, "skipped_count": 0, "error": "Khong tim thay profile Spotify"}

    profile = user.spotify_profile
    access_token = get_valid_access_token(profile)

    qs = Artist.objects.filter(spotify_id__isnull=False).exclude(spotify_id='')
    if not force:
        qs = qs.exclude(image_url__startswith='https://i.scdn.co')

    if limit:
        qs = qs[:limit]

    artists_to_sync = list(qs)
    updated_count = 0
    skipped_count = 0

    for artist in artists_to_sync:
        data = fetch_artist_from_spotify_api(access_token, artist.spotify_id, profile=profile)
        if data:
            images = data.get("images", [])
            genres = data.get("genres", [])
            fields_to_update = []
            if images and images[0].get("url"):
                artist.image_url = images[0]["url"]
                fields_to_update.append("image_url")
            if genres and not artist.genres:
                artist.genres = genres
                fields_to_update.append("genres")
            if fields_to_update:
                artist.save(update_fields=fields_to_update)
                updated_count += 1
            else:
                skipped_count += 1
        else:
            skipped_count += 1
        time.sleep(0.05)

    if updated_count > 0:
        try:
            from analytics.services.caching import invalidate_user_analytics_cache
            invalidate_user_analytics_cache(user.id)
        except Exception:
            pass

    return {
        "total_checked": len(artists_to_sync),
        "updated_count": updated_count,
        "skipped_count": skipped_count
    }

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

def estimate_track_audio_features(track: Track) -> dict:
    """
    Uoc luong Audio Features thuc te dua tren thong tin nghe si, ten bai hat va thoi luong
    khi Spotify Web API chan endpoint /v1/audio-features (HTTP 403 doi voi app moi tu 11/2024).
    """
    import hashlib
    hash_val = int(hashlib.md5(track.spotify_id.encode('utf-8')).hexdigest()[:8], 16)
    variance = (hash_val % 100) / 1000.0

    artist_names = " ".join([a.name.lower() for a in track.artists.all()])
    track_name_lower = track.name.lower()

    edm_keywords = ["alan walker", "thefatrat", "k-391", "lost sky", "arc north", "mountkid", "tokyo machine", "marshmello", "martin garrix", "edm", "remix", "radio edit", "dubstep", "bass"]
    acoustic_keywords = ["acoustic", "piano", "ballad", "vũ", "charlie puth", "dhruv", "taylor", "lofi", "chill", "slowed", "indie"]
    pop_keywords = ["pop", "sơn tùng", "dua lipa", "the weeknd", "bruno mars", "lady gaga", "bts", "blackpink"]

    is_edm = any(kw in artist_names or kw in track_name_lower for kw in edm_keywords)
    is_acoustic = any(kw in artist_names or kw in track_name_lower for kw in acoustic_keywords)
    is_pop = any(kw in artist_names or kw in track_name_lower for kw in pop_keywords)

    if is_edm:
        danceability = min(0.95, 0.72 + variance)
        energy = min(0.98, 0.84 + variance)
        valence = min(0.90, 0.62 + variance)
        acousticness = max(0.04, 0.08 - variance / 2)
        tempo = 126.0 + (hash_val % 15)
    elif is_acoustic:
        danceability = max(0.25, 0.42 + variance)
        energy = max(0.20, 0.38 + variance)
        valence = max(0.25, 0.45 + variance)
        acousticness = min(0.92, 0.75 + variance)
        tempo = 88.0 + (hash_val % 20)
    elif is_pop:
        danceability = min(0.90, 0.68 + variance)
        energy = min(0.88, 0.70 + variance)
        valence = min(0.85, 0.65 + variance)
        acousticness = max(0.10, 0.25 - variance / 2)
        tempo = 112.0 + (hash_val % 22)
    else:
        danceability = 0.55 + ((hash_val % 25) / 100.0)
        energy = 0.58 + (((hash_val >> 2) % 30) / 100.0)
        valence = 0.52 + (((hash_val >> 4) % 25) / 100.0)
        acousticness = 0.25 + (((hash_val >> 6) % 25) / 100.0)
        tempo = 105.0 + (hash_val % 30)

    return {
        "danceability": round(danceability, 3),
        "energy": round(energy, 3),
        "valence": round(valence, 3),
        "acousticness": round(acousticness, 3),
        "tempo": round(tempo, 1),
    }

def sync_audio_features_for_unsynced_tracks(access_token: str, limit: int = 50) -> int:
    """Dong bo cac chi so Audio Features (valence, energy, danceability, v.v.) cho cac bai hat chua co."""
    unsynced_tracks = list(Track.objects.filter(features_synced=False)[:limit])
    if not unsynced_tracks:
        return 0

    track_id_map = {t.spotify_id: t for t in unsynced_tracks}
    features_list = fetch_audio_features_from_api(access_token, list(track_id_map.keys()))

    updated_count = 0
    fetched_ids = set()

    for feat in features_list:
        sp_id = feat.get("id")
        if sp_id in track_id_map:
            fetched_ids.add(sp_id)
            t = track_id_map[sp_id]
            t.danceability = float(feat.get("danceability", 0.0))
            t.energy = float(feat.get("energy", 0.0))
            t.valence = float(feat.get("valence", 0.0))
            t.acousticness = float(feat.get("acousticness", 0.0))
            t.tempo = float(feat.get("tempo", 0.0))
            t.features_synced = True
            t.save(update_fields=["danceability", "energy", "valence", "acousticness", "tempo", "features_synced"])
            updated_count += 1

    # Neu Spotify tra ve 403 hoac rong, tu dong ap dung Audio DSP trich xuat song am 30s va dong bo anh HD
    from tracker.services.audio_dsp import enrich_track_with_dsp_and_artwork
    for sp_id, t in track_id_map.items():
        if sp_id not in fetched_ids:
            enrich_track_with_dsp_and_artwork(t, sync_artist_image=True)
            updated_count += 1

    return updated_count

def sync_user_recently_played_pipeline(user) -> dict:
    """Pipeline hoan chinh: lay token hop le, tinh cursor, fetch Spotify, ingest va sync features."""
    profile = getattr(user, 'spotify_profile', None)
    if not profile or not profile.is_sync_active:
        return {"status": "skipped", "reason": "Sync inactive hoac chua lien ket Spotify profile."}

    access_token = get_valid_access_token(profile)

    now = timezone.now()
    one_day_ago = now - timedelta(days=1)
    last_played = (
        ListeningHistory.objects.filter(user=user)
        .order_by('-played_at')
        .values_list('played_at', flat=True)
        .first()
    )

    total_scrobbled = 0
    sync_mode = "latest_50"

    # Neu co ban ghi cuoi cung trong DB va thuoc 1 ngay gan nhat: cap nhat tiep tu moc do
    if last_played and last_played >= one_day_ago:
        sync_mode = "from_last_played"
        after_ms = int(last_played.timestamp() * 1000)
        payload = fetch_recently_played_from_api(access_token, after_ms=after_ms, limit=50)
        items = payload.get("items", [])

        if items:
            ingest_res = ingest_recently_played_payload(user, payload)
            total_scrobbled += ingest_res.get("scrobbled_count", 0)

            # Phat hien khoang trong du lieu do Spotify gioi han 50 bai (Gap Detection)
            if len(items) == 50:
                try:
                    oldest_item_time = parse_iso_datetime(items[-1]["played_at"])
                    time_gap_seconds = (oldest_item_time - last_played).total_seconds()
                    if time_gap_seconds > 7200:
                        logger.warning(
                            f"[DATA_GAP_DETECTED] User '{user.username}': Phat hien khoang trong "
                            f"{time_gap_seconds / 3600:.1f}h giua ban ghi DB ({last_played.isoformat()}) "
                            f"va bai cu nhat Spotify tra ve ({oldest_item_time.isoformat()}). "
                            f"Cac bai hat o giua da bi troi khoi bo dem 50 bai cua Spotify."
                        )
                except Exception as gap_err:
                    logger.debug(f"Gap detection check error: {gap_err}")
        else:
            # Fallback kiem tra 50 bai gan nhat (khong after) de chong lech dong ho may chu
            fallback_payload = fetch_recently_played_from_api(access_token, after_ms=None, limit=50)
            fallback_ingest = ingest_recently_played_payload(user, fallback_payload)
            total_scrobbled += fallback_ingest.get("scrobbled_count", 0)
    else:
        # Mac dinh lay 50 bai gan nhat (khi DB chua co hoac ban ghi cuoi da qua 1 ngay)
        sync_mode = "latest_50"
        payload = fetch_recently_played_from_api(access_token, after_ms=None, limit=50)
        ingest_res = ingest_recently_played_payload(user, payload)
        total_scrobbled += ingest_res.get("scrobbled_count", 0)

    # Dong bo Audio Features cho cac bai hat chua co features (toi da 100 tracks)
    features_synced_count = sync_audio_features_for_unsynced_tracks(access_token, limit=100)

    # Dong bo avatar chinh chu tu Spotify cho cac nghe si moi chua co anh (toi da 20 artists)
    sync_artist_images_from_spotify(user=user, limit=20, force=False)

    # Xoa cache thong ke cu de dam bao dashboard phan anh du lieu moi nhat
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
        "sync_mode": sync_mode,
        "scrobbled_count": total_scrobbled,
        "features_synced_count": features_synced_count,
        "last_synced_at": profile.last_synced_at.isoformat(),
    }
