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

