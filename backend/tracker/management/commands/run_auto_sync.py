"""
Management command: Chay tien trinh Auto-Sync Daemon doc lap khong can Redis / Celery.
Tu dong dong bo lich su nghe nhac Spotify dinh ky cho toan bo nguoi dung dang active.
"""

import sys
import time
import signal
from datetime import datetime
from django.core.management.base import BaseCommand
from users.models import SpotifyProfile
from tracker.services.ingestion import sync_user_recently_played_pipeline

class Command(BaseCommand):
    help = "Chay daemon tu dong dong bo Spotify dinh ky ma khong can Redis hay Celery."

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=15,
            help='Khoang thoi gian giua cac lan sync tinh bang phut (mac dinh: 15 phut).'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Chi thuc thi 1 chu ky roi thoat ngay (dung cho cron job hoac test).'
        )

    def handle(self, *args, **options):
        interval_minutes = max(options['interval'], 1)
        run_once = options['once']

        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

        self.stdout.write(
            self.style.SUCCESS(
                f"Khoi dong Auto-Sync Daemon (chu ky: {interval_minutes} phut, run_once={run_once})."
            )
        )
        self.stdout.write("Nhan Ctrl + C bat ky luc nao de dung tien trinh an toan.\n")

        shutdown_requested = False

        def handle_sigint(sig, frame):
            nonlocal shutdown_requested
            shutdown_requested = True
            self.stdout.write("\nNhan tin hieu dung (Ctrl+C). Dang hoan tat va thoat an toan...")

        signal.signal(signal.SIGINT, handle_sigint)

        cycle_count = 0

        while not shutdown_requested:
            cycle_count += 1
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.stdout.write(f"[{now_str}] Chu ky #{cycle_count}: Bat dau quet nguoi dung active...")

            active_profiles = (
                SpotifyProfile.objects.filter(is_sync_active=True)
                .select_related('user')
            )
            total_active = active_profiles.count()

            if total_active == 0:
                self.stdout.write("  Khong co nguoi dung nao dang bat is_sync_active.")
            else:
                for profile in active_profiles:
                    if shutdown_requested:
                        break
                    user = profile.user
                    try:
                        res = sync_user_recently_played_pipeline(user)
                        status_str = res.get("status", "unknown")
                        scrobbled = res.get("scrobbled_count", 0)
                        features = res.get("features_synced_count", 0)
                        mode = res.get("sync_mode", "")
                        self.stdout.write(
                            f"  - User '{user.username}': status={status_str}, "
                            f"new_tracks={scrobbled}, features={features}, mode={mode}"
                        )
                    except Exception as e:
                        self.stderr.write(f"  - Loi khi dong bo user '{user.username}': {str(e)}")

            if run_once or shutdown_requested:
                break

            self.stdout.write(
                f"Hoan tat chu ky #{cycle_count}. Tam nghi {interval_minutes} phut cho den lan tiep theo...\n"
            )

            # Chia nho sleep thanh tung giay de bat Ctrl+C ngay lap tuc
            sleep_seconds = interval_minutes * 60
            for _ in range(sleep_seconds):
                if shutdown_requested:
                    break
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS("Da dung Auto-Sync Daemon an toan."))
