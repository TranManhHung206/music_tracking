"""
Unit tests cho app analytics.
Kiem tra tinh toan thong ke ORM, chuan hoa bieu do, chuoi thoi gian don dieu va co che Caching.
"""

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from tracker.models import Artist, Album, Track, ListeningHistory
from analytics.services.caching import (
    build_analytics_cache_key,
    get_or_set_cached_metric,
    invalidate_user_analytics_cache,
)
from analytics.services.filters import get_time_range_bounds, get_cache_ttl_for_range

class AnalyticsBaseTestCase(APITestCase):
    """Lop co so thiet lap du lieu mau cho kiem thu Analytics."""

    def setUp(self):
        self.user = User.objects.create_user(username='analytic_user', password='password123')
        self.client.force_authenticate(user=self.user)

        self.artist1 = Artist.objects.create(spotify_id='art_1', name='Sơn Tùng M-TP')
        self.artist2 = Artist.objects.create(spotify_id='art_2', name='Đen Vâu')

        self.album1 = Album.objects.create(
            spotify_id='alb_1',
            name='Chúng Ta',
            release_date='2024-03-08',
            image_url='https://example.com/cover1.jpg',
        )

        self.track1 = Track.objects.create(
            spotify_id='trk_1',
            name='Chúng Ta Của Tương Lai',
            album=self.album1,
            duration_ms=240000,
            valence=0.8,
            energy=0.75,
            danceability=0.65,
            acousticness=0.2,
            tempo=128.0,
            features_synced=True,
        )
        self.track1.artists.add(self.artist1)

        self.track2 = Track.objects.create(
            spotify_id='trk_2',
            name='Nấu Ăn Cho Em',
            album=self.album1,
            duration_ms=180000,
            valence=0.5,
            energy=0.4,
            danceability=0.55,
            acousticness=0.8,
            tempo=95.0,
            features_synced=True,
        )
        self.track2.artists.add(self.artist2)

        # Tao lich su nghe nhac
        now = timezone.now()
        # 3 luot nghe track1
        ListeningHistory.objects.create(user=self.user, track=self.track1, played_at=now - timedelta(days=2))
        ListeningHistory.objects.create(user=self.user, track=self.track1, played_at=now - timedelta(days=5))
        ListeningHistory.objects.create(user=self.user, track=self.track1, played_at=now - timedelta(days=10))

        # 2 luot nghe track2
        ListeningHistory.objects.create(user=self.user, track=self.track2, played_at=now - timedelta(days=1))
        ListeningHistory.objects.create(user=self.user, track=self.track2, played_at=now - timedelta(days=15))

class SummaryAnalyticsTests(AnalyticsBaseTestCase):
    """Kiem thu endpoint tong quan /api/analytics/summary/."""

    def test_summary_returns_correct_aggregates(self):
        url = '/api/analytics/summary/?time_range=30d'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['total_plays'], 5)
        self.assertEqual(data['unique_artists_count'], 2)
        self.assertEqual(data['unique_albums_count'], 1)
        expected_duration = (3 * 240000) + (2 * 180000)
        self.assertEqual(data['total_duration_ms'], expected_duration)
        self.assertAlmostEqual(data['total_hours'], round(expected_duration / 3600000, 2))

    def test_summary_filter_7d_limits_records(self):
        url = '/api/analytics/summary/?time_range=7d'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        # Trong 7 ngay co 2 luot track1 (days=2, days=5) va 1 luot track2 (days=1) = 3 luot
        self.assertEqual(data['total_plays'], 3)

class TopTracksAndArtistsTests(AnalyticsBaseTestCase):
    """Kiem thu Top Tracks va Top Artists."""

    def test_top_tracks_ordering(self):
        url = '/api/analytics/top-tracks/?time_range=30d&limit=10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tracks = response.json().get('tracks', [])
        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0]['spotify_id'], 'trk_1')
        self.assertEqual(tracks[0]['play_count'], 3)
        self.assertEqual(tracks[1]['spotify_id'], 'trk_2')
        self.assertEqual(tracks[1]['play_count'], 2)

    def test_top_artists_ordering(self):
        url = '/api/analytics/top-artists/?time_range=30d&limit=10'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        artists = response.json().get('artists', [])
        self.assertEqual(len(artists), 2)
        self.assertEqual(artists[0]['name'], 'Sơn Tùng M-TP')
        self.assertEqual(artists[0]['play_count'], 3)

class RadarAndHeatmapTests(AnalyticsBaseTestCase):
    """Kiem thu chuan hoa Radar va ma tran Heatmap."""

    def test_radar_features_normalized_bounds(self):
        url = '/api/analytics/radar/?time_range=30d'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('features', data)
        self.assertGreaterEqual(len(data['features']), 4)
        for feat in data['features']:
            self.assertIn('attribute', feat)
            self.assertIn('score', feat)
            self.assertTrue(0.0 <= feat['score'] <= 1.0, f"Score out of bounds: {feat}")

    def test_heatmap_matrix_dimensions(self):
        url = '/api/analytics/heatmap/?time_range=30d'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        matrix = data.get('matrix', [])
        self.assertEqual(len(matrix), 7 * 24)
        for cell in matrix:
            self.assertTrue(1 <= cell['day_of_week'] <= 7)
            self.assertTrue(0 <= cell['hour'] <= 23)
            self.assertGreaterEqual(cell['count'], 0)

    def test_heatmap_month_calendar(self):
        url = '/api/analytics/heatmap/?time_range=month&period_type=month'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data.get('period_type'), 'month')
        self.assertIn('month_calendar', data)
        month_cal = data['month_calendar']
        self.assertIn('days', month_cal)
        self.assertTrue(28 <= len(month_cal['days']) <= 31)
        self.assertIn('total_plays', month_cal)
        self.assertIn('peak_day', month_cal)

    def test_heatmap_month_calendar_clamped_when_range_too_long(self):
        url = '/api/analytics/heatmap/?start_date=2026-01-01&end_date=2026-12-31&period_type=month'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data.get('period_type'), 'month')
        self.assertIn('month_calendar', data)
        self.assertEqual(len(data['month_calendar']['days']), 31)

    def test_heatmap_year_calendar(self):
        url = '/api/analytics/heatmap/?time_range=year&period_type=year'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data.get('period_type'), 'year')
        self.assertIn('year_calendar', data)
        year_cal = data['year_calendar']
        self.assertIn('days', year_cal)
        self.assertGreaterEqual(len(year_cal['days']), 365)
        self.assertIn('months_header', year_cal)
        self.assertIn('longest_streak', year_cal)

class BarChartRaceTests(AnalyticsBaseTestCase):
    """Kiem thu chuoi thoi gian luy ke don dieu cua Bar Chart Race."""

    def test_bar_chart_race_monotonicity(self):
        url = '/api/analytics/bar-chart-race/?time_range=1y'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        timeline = data.get('timeline', [])
        self.assertGreaterEqual(len(timeline), 2)

        # Kiem tra tinh tang don dieu cua cumulative_plays
        artist_cumulative = {}
        for frame in timeline:
            for rank_item in frame['rankings']:
                art_name = rank_item['name']
                curr_cum = rank_item['cumulative_plays']
                if art_name in artist_cumulative:
                    self.assertGreaterEqual(
                        curr_cum,
                        artist_cumulative[art_name],
                        f"Cumulative plays decreased for {art_name}"
                    )
                artist_cumulative[art_name] = curr_cum

class CachingAndSecurityTests(AnalyticsBaseTestCase):
    """Kiem thu co che Caching va bao mat quyen truy cap."""

    def test_unauthenticated_request_rejected(self):
        self.client.logout()
        response = self.client.get('/api/analytics/summary/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_cache_fallback_resilience(self):
        cache_key = build_analytics_cache_key(self.user.id, 'test_metric', '30d')
        ttl = get_cache_ttl_for_range('30d')
        called = {'count': 0}

        def mock_compute():
            called['count'] += 1
            return {'result': 42}

        # Lan 1: Miss -> compute
        res1 = get_or_set_cached_metric(cache_key, ttl, mock_compute)
        self.assertEqual(res1, {'result': 42})
        self.assertEqual(called['count'], 1)

        # Lan 2: Hit -> khong goi compute lai
        res2 = get_or_set_cached_metric(cache_key, ttl, mock_compute)
        self.assertEqual(res2, {'result': 42})
        self.assertEqual(called['count'], 1)

        # Invalidate cache
        invalidate_user_analytics_cache(self.user.id)

    def test_time_filters_bounds(self):
        s_dt, e_dt, key = get_time_range_bounds('7d')
        self.assertEqual(key, '7d')
        self.assertLess(s_dt, e_dt)

        s_dt, e_dt, key = get_time_range_bounds('custom', '2025-01-01', '2025-01-31')
        self.assertTrue(key.startswith('period_'))

        s_dt, e_dt, key = get_time_range_bounds(start_date_str='2026-10-01', end_date_str='2026-10-31')
        self.assertEqual(key, 'period_2026-10-01_2026-10-31')

class CalendarPeriodsTests(AnalyticsBaseTestCase):
    """Kiem thu danh sach ky lich thoi gian va pham vi khong co du lieu."""

    def test_calendar_periods_endpoint_week(self):
        url = '/api/analytics/periods/?period_type=week&limit=6'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['period_type'], 'week')
        self.assertEqual(len(data['periods']), 6)
        # Ky dau tien bat buoc la hien tai
        self.assertTrue(data['periods'][0]['is_current'])
        # Cac ky tiep theo phai la qua khu
        for p in data['periods'][1:]:
            self.assertFalse(p['is_current'])
            self.assertLessEqual(p['start_date'], data['periods'][0]['start_date'])

    def test_calendar_periods_endpoint_month(self):
        url = '/api/analytics/periods/?period_type=month&limit=4'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['period_type'], 'month')
        self.assertEqual(len(data['periods']), 4)
        self.assertTrue(data['periods'][0]['is_current'])
        self.assertFalse(data['periods'][1]['is_current'])

    def test_calendar_periods_endpoint_year(self):
        url = '/api/analytics/periods/?period_type=year&limit=3'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['period_type'], 'year')
        self.assertEqual(len(data['periods']), 3)
        self.assertTrue(data['periods'][0]['is_current'])

    def test_calendar_period_empty_summary(self):
        # Truy van khoang thoi gian xa trong qua khu ma nguoi dung chua co du lieu
        url = '/api/analytics/summary/?start_date=2020-01-01&end_date=2020-01-07'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total_plays'], 0)
        self.assertEqual(data['unique_artists_count'], 0)

    def test_calendar_periods_unauthenticated(self):
        self.client.logout()
        response = self.client.get('/api/analytics/periods/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

class HybridGenreClassificationTests(AnalyticsBaseTestCase):
    """Kiem thu he thong phan loai the loai am nhac lai Hybrid Genre Classifier."""

    def test_hybrid_genre_classification_logic(self):
        from analytics.services.calculations import classify_artist_genres

        # 1. Bai hat Viet Nam Acoustic / Indie
        track_acoustic = Track(name='Tự', energy=0.40, acousticness=0.85, danceability=0.45, tempo=85.0)
        genre_ac = classify_artist_genres('Thịnh Suy', 'Tự', artists=['Thịnh Suy'], track=track_acoustic)
        self.assertEqual(genre_ac, 'V-Pop')

        track_sivan = Track(name='Để Dành Khi Thức Giấc', energy=0.69, acousticness=0.85, danceability=0.49, tempo=129.0)
        genre_sivan = classify_artist_genres('SIVAN', 'Để Dành Khi Thức Giấc', artists=['SIVAN'], track=track_sivan)
        self.assertEqual(genre_sivan, 'V-Pop')

        # 2. Bai hat Viet Nam Electronic / Dance
        track_dance = Track(name='Ngẫu Hứng', energy=0.88, acousticness=0.15, danceability=0.75, tempo=130.0)
        genre_ed = classify_artist_genres('Hoaprox', 'Ngẫu Hứng', artists=['Hoaprox'], track=track_dance)
        self.assertEqual(genre_ed, 'V-Pop')

        # 3. Bai hat Quoc te EDM / Electronic
        track_edm = Track(name='Faded', energy=0.85, acousticness=0.10, danceability=0.60, tempo=126.0)
        genre_edm = classify_artist_genres('Alan Walker', 'Faded', artists=['Alan Walker'], track=track_edm)
        self.assertEqual(genre_edm, 'EDM / Electronic')

        # 4. Bai hat Quoc te Acoustic / Lo-Fi
        track_lofi = Track(name='double take', energy=0.35, acousticness=0.75, danceability=0.40, tempo=90.0)
        genre_lofi = classify_artist_genres('Dhruv', 'double take', artists=['Dhruv'], track=track_lofi)
        self.assertEqual(genre_lofi, 'Acoustic / Lo-Fi')

    def test_genre_distribution_api_endpoint(self):
        url = '/api/analytics/genres/?time_range=30d'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('genres', data)
        self.assertIn('total_plays', data)
        self.assertIn('top_genre', data)
        self.assertGreater(data['total_plays'], 0)
        self.assertIsInstance(data['genres'], list)
        self.assertGreater(len(data['genres']), 0)
        for g in data['genres']:
            self.assertIn('name', g)
            self.assertIn('plays', g)
            self.assertIn('percentage', g)
            self.assertIn('color', g)
            self.assertTrue(g['color'].startswith('#'))

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from django.core.management import call_command
from analytics.services import calculations

class ArtistCSVClassificationTests(APITestCase):
    """Kiem thu chuc nang xu ly file CSV phan loai nghe si va nhan New."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_data_dir = calculations.DATA_DIR
        calculations.DATA_DIR = Path(self.temp_dir)
        calculations._ALL_CSV_ARTIST_NAMES.clear()
        calculations._CUSTOM_ARTISTS_LOADED = False
        calculations._LAST_CSV_MTIME = 0.0

    def tearDown(self):
        calculations.DATA_DIR = self.orig_data_dir
        calculations._ALL_CSV_ARTIST_NAMES.clear()
        calculations._CUSTOM_ARTISTS_LOADED = False
        calculations._LAST_CSV_MTIME = 0.0
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_custom_artist_dataset_skips_new_notes(self):
        csv_path = Path(self.temp_dir) / "test_artists.csv"
        with open(csv_path, mode="w", encoding="utf-8-sig") as f:
            f.write("spotify_name,is_vpop,notes\n")
            f.write("Confirmed VN,1.0,\n")
            f.write("Confirmed Foreign,0.0,\n")
            f.write("Pending VN,1.0,New\n")
            f.write("Pending Foreign,0.0,New\n")
            f.write("Pending CaseInsensitive,0,new\n")

        vn, foreign = calculations.load_custom_artist_dataset()

        self.assertIn("confirmed vn", vn)
        self.assertIn("confirmed foreign", foreign)
        self.assertNotIn("pending vn", vn)
        self.assertNotIn("pending foreign", foreign)
        self.assertNotIn("pending vn", foreign)
        self.assertNotIn("pending foreign", vn)
        self.assertNotIn("pending caseinsensitive", foreign)
        self.assertIn("pending foreign", calculations._ALL_CSV_ARTIST_NAMES)
        self.assertIn("confirmed vn", calculations._ALL_CSV_ARTIST_NAMES)

    def test_register_unclassified_artists_batch_and_deduplication(self):
        added = calculations.register_unclassified_artists_batch(["New Artist 1", "New Artist 2"])
        self.assertEqual(added, 2)

        csv_file = Path(self.temp_dir) / "vietnamese_artist.csv"
        self.assertTrue(csv_file.exists())

        with open(csv_file, mode="r", encoding="utf-8-sig") as f:
            content = f.read()
        self.assertIn("New Artist 1,0,New", content)
        self.assertIn("New Artist 2,0,New", content)

        # Kiem tra chong trung lap
        added_again = calculations.register_unclassified_artists_batch(["new artist 1", "New Artist 2", "New Artist 3"])
        self.assertEqual(added_again, 1)

    def test_sync_missing_artists_command(self):
        from io import StringIO
        Artist.objects.create(spotify_id="cmd_art_1", name="Command Artist Test")
        out = StringIO()
        call_command("sync_missing_artists_to_csv", stdout=out)
        output = out.getvalue()
        self.assertIn("Tong so nghe si", output)
        self.assertIn("Hoan tat dong bo", output)

