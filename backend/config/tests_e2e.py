"""
End-to-End System Integration Tests (Giai doan 6).
Kiem thu toan dien luong nghiep vu, bao mat Zero-Leakage (NFR-2), va hieu nang Caching (NFR-1).
"""

import time
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from users.models import SpotifyProfile
from users.services.encryption import encrypt_token, decrypt_token
from tracker.models import Artist, Album, Track, ListeningHistory
from tracker.services.ingestion import ingest_recently_played_payload
from ai_engine.models import AIMusicPersona

class EndToEndSystemIntegrationTests(APITestCase):
    """Kiem thu tich hop toan dien toan bo he thong tu OAuth, Tracker, Analytics den AI Engine."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user(
            username='e2e_user',
            email='e2e@example.com',
            password='Password123!',
            first_name='Hùng',
            last_name='Trần'
        )
        self.client.force_authenticate(user=self.user)

        # Tao Spotify Profile voi token duoc ma hoa AES-256
        self.raw_access_token = "BQA_dummy_spotify_access_token_12345"
        self.raw_refresh_token = "AQB_dummy_spotify_refresh_token_67890"

        self.profile = SpotifyProfile.objects.create(
            user=self.user,
            spotify_id='spotify_e2e_user_id',
            display_name='Hùng Trần',
            email='e2e@example.com',
            encrypted_access_token=encrypt_token(self.raw_access_token),
            encrypted_refresh_token=encrypt_token(self.raw_refresh_token),
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_sync_active=True,
        )

    def test_nfr2_security_zero_leakage_and_encryption(self):
        """Kiem tra NFR-2: Tuyet doi khong lo token trong API response va luu ma hoa trong DB."""
        # 1. Kiem tra API /api/users/me/
        res = self.client.get('/api/users/me/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user_data = res.json().get('user', res.json())

        # Khong duoc chua bat ky truong token nao
        self.assertNotIn('encrypted_access_token', user_data)
        self.assertNotIn('encrypted_refresh_token', user_data)
        self.assertNotIn('access_token', user_data)
        self.assertNotIn('refresh_token', user_data)

        # 2. Kiem tra du lieu luu trong Database
        db_profile = SpotifyProfile.objects.get(user=self.user)
        # Token phai duoc ma hoa bang Fernet (bat dau bang gAAAAA)
        self.assertTrue(db_profile.encrypted_access_token.startswith('gAAAAA'))
        self.assertNotEqual(db_profile.encrypted_access_token, self.raw_access_token)
        # Giai ma trong memory phai dung voi token ban dau
        self.assertEqual(decrypt_token(db_profile.encrypted_access_token), self.raw_access_token)

    def test_e2e_ingestion_and_analytics_pipeline(self):
        """Kiem tra luong cào du lieu, deduplication va tinh toan thong ke Analytics."""
        played_time_1 = timezone.now().isoformat()
        played_time_2 = (timezone.now() - timedelta(minutes=10)).isoformat()

        # Gia lap Spotify Recently Played Payload voi 2 items
        mock_payload = {
            "items": [
                {
                    "track": {
                        "id": "trk_e2e_1",
                        "name": "Chúng Ta Của Tương Lai",
                        "duration_ms": 240000,
                        "artists": [{"id": "art_e2e_1", "name": "Sơn Tùng M-TP"}],
                        "album": {
                            "id": "alb_e2e_1",
                            "name": "Chúng Ta",
                            "release_date": "2024-03-08",
                            "images": [{"url": "https://example.com/cover1.jpg"}]
                        }
                    },
                    "played_at": played_time_1,
                    "context": {"type": "playlist"}
                },
                {
                    "track": {
                        "id": "trk_e2e_2",
                        "name": "Nấu Ăn Cho Em",
                        "duration_ms": 180000,
                        "artists": [{"id": "art_e2e_2", "name": "Đen Vâu"}],
                        "album": {
                            "id": "alb_e2e_2",
                            "name": "Nấu Ăn Cho Em",
                            "release_date": "2023-05-13",
                            "images": [{"url": "https://example.com/cover2.jpg"}]
                        }
                    },
                    "played_at": played_time_2,
                    "context": {"type": "album"}
                }
            ]
        }

        # Lan 1: Ingest 2 bai hat
        result_1 = ingest_recently_played_payload(self.user, mock_payload)
        self.assertGreaterEqual(result_1["scrobbled_count"], 1)
        self.assertEqual(ListeningHistory.objects.filter(user=self.user).count(), 2)

        # Lan 2: Ingest lai cung payload -> Database khong bi tang them ban ghi
        result_2 = ingest_recently_played_payload(self.user, mock_payload)
        self.assertIn(result_2["scrobbled_count"], [0, 2])
        self.assertEqual(ListeningHistory.objects.filter(user=self.user).count(), 2)

        # Gan Audio Features cho cac track de phuc vu Radar
        Track.objects.filter(spotify_id="trk_e2e_1").update(
            valence=0.7, energy=0.8, danceability=0.75, acousticness=0.2, tempo=128.0, features_synced=True
        )
        Track.objects.filter(spotify_id="trk_e2e_2").update(
            valence=0.5, energy=0.4, danceability=0.6, acousticness=0.85, tempo=95.0, features_synced=True
        )

        from django.core.cache import cache
        cache.clear()

        # Kiem tra API Analytics Summary
        res_sum = self.client.get('/api/analytics/summary/?time_range=30d')
        self.assertEqual(res_sum.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sum.json()['total_plays'], 2)
        self.assertEqual(res_sum.json()['unique_artists_count'], 2)

        # Kiem tra API Radar Features
        res_radar = self.client.get('/api/analytics/radar/?time_range=30d')
        self.assertEqual(res_radar.status_code, status.HTTP_200_OK)
        radar_feats = res_radar.json()['features']
        self.assertGreaterEqual(len(radar_feats), 4)

        # Kiem tra API Heatmap 24x7
        res_heat = self.client.get('/api/analytics/heatmap/?time_range=30d')
        self.assertEqual(res_heat.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_heat.json()['matrix']), 7 * 24)

    def test_nfr1_performance_and_caching_speed(self):
        """Kiem tra NFR-1: Thoi gian phan hoi API < 1.5s va cache hit cuc nhanh."""
        # Tao 1 ban ghi lich su
        track = Track.objects.create(
            spotify_id='trk_perf',
            name='Performance Track',
            duration_ms=200000,
            features_synced=True
        )
        ListeningHistory.objects.create(user=self.user, track=track, played_at=timezone.now())

        url = '/api/analytics/summary/?time_range=30d'

        # Lan 1: Cache Miss -> Thoi gian phai nho hon 1.5 giay
        t0 = time.time()
        res_1 = self.client.get(url)
        t_miss = time.time() - t0
        self.assertEqual(res_1.status_code, status.HTTP_200_OK)
        self.assertLess(t_miss, 1.5, f"Cache miss vuot qua 1.5s: {t_miss}s")

        # Lan 2: Cache Hit -> Thoi gian phan hoi duoi 100ms
        t1 = time.time()
        res_2 = self.client.get(url)
        t_hit = time.time() - t1
        self.assertEqual(res_2.status_code, status.HTTP_200_OK)
        self.assertLess(t_hit, 0.15, f"Cache hit vuot qua 150ms: {t_hit}s")

    def test_e2e_ai_persona_and_recommendations(self):
        """Kiem tra phan he AI Persona va KNN Recommendations hoat dong gan ket."""
        # Tao 2 tracks co Audio Features
        trk1 = Track.objects.create(
            spotify_id='trk_ai_seed',
            name='Giai Dieu 1',
            danceability=0.8,
            energy=0.9,
            valence=0.7,
            acousticness=0.1,
            tempo=130.0,
            features_synced=True,
        )
        trk2 = Track.objects.create(
            spotify_id='trk_ai_cand',
            name='Giai Dieu 2',
            danceability=0.78,
            energy=0.88,
            valence=0.68,
            acousticness=0.12,
            tempo=128.0,
            features_synced=True,
        )

        # 1. Sinh AI Persona qua POST API
        res_p = self.client.post('/api/ai/persona/generate/', {'period_type': 'monthly'})
        self.assertEqual(res_p.status_code, status.HTTP_201_CREATED)
        persona_data = res_p.json()
        self.assertIn('persona_title', persona_data)
        self.assertEqual(sum(persona_data['mood_distribution'].values()), 100)
        self.assertEqual(AIMusicPersona.objects.filter(user=self.user).count(), 1)

        # 2. Goi KNN Recommendation qua GET API
        res_rec = self.client.get(f'/api/ai/recommendations/?track_id={trk1.spotify_id}&top_k=2')
        self.assertEqual(res_rec.status_code, status.HTTP_200_OK)
        rec_json = res_rec.json()
        self.assertEqual(rec_json['seed_track']['spotify_id'], trk1.spotify_id)
        self.assertGreaterEqual(len(rec_json['recommendations']), 1)
        self.assertEqual(rec_json['recommendations'][0]['spotify_id'], trk2.spotify_id)
        self.assertGreater(rec_json['recommendations'][0]['similarity_score'], 0.8)
