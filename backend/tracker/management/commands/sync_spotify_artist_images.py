"""
Management command dong bo anh dai dien chinh chu va genres tu Spotify API cho toan bo nghe si theo spotify_id.
"""

import sys
import time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.models import Artist
from tracker.services.ingestion import fetch_artist_from_spotify_api
from users.services.spotify_auth import get_valid_access_token
from analytics.services.caching import invalidate_user_analytics_cache

def safe_str(text: str) -> str:
    """Xu ly chuoi an toan tren console Windows de tranh loi cp1252."""
    if not text:
        return ""
    try:
        return text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
    except Exception:
        return text.encode('ascii', errors='replace').decode('ascii')

class Command(BaseCommand):
    help = "Dong bo anh dai dien chinh chu va the loai (genres) tu Spotify Web API theo ma spotify_id cua tung nghe si."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Buoc dong bo lai toan bo ke ca nghe si da co anh Spotify.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Gioi han so luong nghe si can dong bo.',
        )

    def handle(self, *args, **options):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

        force = options.get('force', False)
        limit = options.get('limit')

        user = User.objects.filter(spotify_profile__isnull=False, spotify_profile__is_sync_active=True).first()
        if not user:
            user = User.objects.filter(spotify_profile__isnull=False).first()

        if not user or not hasattr(user, 'spotify_profile') or not user.spotify_profile:
            self.stderr.write("Loi: Khong tim thay nguoi dung nao co Spotify profile hop le de lay token.")
            return

        profile = user.spotify_profile
        access_token = get_valid_access_token(profile)

        qs = Artist.objects.filter(spotify_id__isnull=False).exclude(spotify_id='')
        if not force:
            qs = qs.exclude(image_url__startswith='https://i.scdn.co')

        total_artists = qs.count()
        if limit:
            qs = qs[:limit]
            total_artists = min(total_artists, limit)

        self.stdout.write(f"Bat dau dong bo anh Spotify chinh chu cho {total_artists} nghe si (user: {user.username})...")

        updated_count = 0
        skipped_count = 0

        for idx, artist in enumerate(qs, start=1):
            clean_name = safe_str(artist.name)
            data = fetch_artist_from_spotify_api(access_token, artist.spotify_id, profile=profile)
            if data:
                images = data.get("images", [])
                genres = data.get("genres", [])
                fields = []

                if images and images[0].get("url"):
                    artist.image_url = images[0]["url"]
                    fields.append("image_url")
                if genres:
                    artist.genres = genres
                    fields.append("genres")

                if fields:
                    artist.save(update_fields=fields)
                    updated_count += 1
                    img_preview = artist.image_url[:55] + "..." if artist.image_url and len(artist.image_url) > 55 else artist.image_url
                    self.stdout.write(f"[{idx}/{total_artists}] {clean_name} ({artist.spotify_id}) -> {img_preview}")
                else:
                    skipped_count += 1
                    self.stdout.write(f"[{idx}/{total_artists}] {clean_name} -> Khong co anh tren Spotify.")
            else:
                skipped_count += 1
                self.stdout.write(f"[{idx}/{total_artists}] {clean_name} -> API loi hoac rate limit.")

            time.sleep(0.06)

        # Xoa cache analytics
        for u in User.objects.all():
            invalidate_user_analytics_cache(u.id)

        self.stdout.write("=" * 60)
        self.stdout.write(f"HOAN TAT: Da cap nhat {updated_count} nghe si, bo qua {skipped_count} nghe si.")
        self.stdout.write("Da xoa toan bo cache analytics de cap nhat avatar moi len giao dien.")
