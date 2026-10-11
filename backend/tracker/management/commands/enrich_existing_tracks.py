"""
Management command de nang cap toan bo cac bai hat hien co trong Database len du lieu DSP song am that va anh nghe si HD.
"""

import sys
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tracker.models import Track
from tracker.services.audio_dsp import enrich_track_with_dsp_and_artwork
from analytics.services.caching import invalidate_user_analytics_cache

def safe_str(text: str) -> str:
    """Loai bo loi ma hoa Unicode cp1252 tren Windows console."""
    if not text:
        return ""
    try:
        return text.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8')
    except Exception:
        return text.encode('ascii', errors='replace').decode('ascii')

class Command(BaseCommand):
    help = "Quet toan bo cac bai hat trong DB va nang cap len du lieu song am that kem anh nghe si 1000x1000."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Buoc phan tich lai toan bo ca nhung bai da sync cu.',
        )

    def handle(self, *args, **options):
        # Cau hinh utf-8 cho stdout neu co the
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

        tracks_qs = Track.objects.all()
        total_tracks = tracks_qs.count()

        self.stdout.write(f"Bat dau nang cap {total_tracks} bai hat trong Database...")

        success_count = 0
        fallback_count = 0

        for idx, track in enumerate(tracks_qs, start=1):
            artist_names = ", ".join([a.name for a in track.artists.all()])
            clean_track_name = safe_str(track.name)
            clean_artist_names = safe_str(artist_names)
            
            try:
                self.stdout.write(f"[{idx}/{total_tracks}] Dang xu ly: {clean_track_name} - {clean_artist_names}")
            except Exception:
                self.stdout.write(f"[{idx}/{total_tracks}] Dang xu ly track_id={track.id}")

            is_dsp_success = enrich_track_with_dsp_and_artwork(track, sync_artist_image=True)
            if is_dsp_success:
                success_count += 1
                self.stdout.write(f"  -> DSP Thanh cong: BPM={track.tempo}, Energy={track.energy}, Acoustic={track.acousticness}")
            else:
                fallback_count += 1
                self.stdout.write(f"  -> Ap dung Fallback: Energy={track.energy}, Acoustic={track.acousticness}")

        # Xoa cache analytics cua tat ca nguoi dung de bieu do cap nhat so lieu moi ngay
        for u in User.objects.all():
            invalidate_user_analytics_cache(u.id)

        self.stdout.write("=" * 60)
        self.stdout.write(f"HOAN TAT NANG CAP: {total_tracks} bai hat (DSP that: {success_count}, Fallback: {fallback_count})")
        self.stdout.write("Da xoa toan bo cache analytics de cap nhat bieu do.")
