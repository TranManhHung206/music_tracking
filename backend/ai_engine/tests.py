"""
Unit tests cho app ai_engine.
Kiem tra model AIMusicPersona, Vectorization am thanh, KNN Recommender va cac AI API Endpoints.
"""

from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from tracker.models import Artist, Album, Track, ListeningHistory
from ai_engine.models import AIMusicPersona
from ai_engine.services.knn_recommender import (
    normalize_tempo,
    extract_track_vector,
    get_song_recommendations,
)
from ai_engine.services.ai_persona import (
    generate_heuristic_persona,
    extract_user_music_context,
    generate_and_save_persona,
)

class AIEngineBaseTestCase(APITestCase):
    """Lop co so thiet lap du lieu kiem thu cho AI Engine."""

    def setUp(self):
        self.user = User.objects.create_user(username='ai_user', password='password123')
        self.client.force_authenticate(user=self.user)

        self.artist = Artist.objects.create(spotify_id='art_ai_1', name='Phan Mạnh Quỳnh')
        self.album = Album.objects.create(spotify_id='alb_ai_1', name='Album Mẫu')

        # Track 1: Seed track (Phong cach mộc, buồn)
        self.seed_track = Track.objects.create(
            spotify_id='trk_seed',
            name='Có Chàng Trai Viết Lên Cây',
            album=self.album,
            duration_ms=210000,
            danceability=0.4,
            energy=0.3,
            valence=0.25,
            acousticness=0.85,
            tempo=85.0,
            features_synced=True,
        )
        self.seed_track.artists.add(self.artist)

        # Track 2: Similar track (Cung phong cach mộc, acoustic cao)
        self.similar_track = Track.objects.create(
            spotify_id='trk_sim',
            name='Ngày Chưa Giông Bão',
            album=self.album,
            duration_ms=230000,
            danceability=0.42,
            energy=0.35,
            valence=0.28,
            acousticness=0.80,
            tempo=88.0,
            features_synced=True,
        )
        self.similar_track.artists.add(self.artist)

        # Track 3: Distant track (Sôi động, điện tử)
        self.distant_track = Track.objects.create(
            spotify_id='trk_dist',
            name='Vũ Điệu Hoang Dã',
            album=self.album,
            duration_ms=190000,
            danceability=0.9,
            energy=0.95,
            valence=0.85,
            acousticness=0.05,
            tempo=135.0,
            features_synced=True,
        )
        self.distant_track.artists.add(self.artist)

class VectorizationAndKNNTests(AIEngineBaseTestCase):
    """Kiem thu tinh toan vector am thanh va thuat toan KNN."""

    def test_normalize_tempo_bounds(self):
        self.assertEqual(normalize_tempo(40.0), 0.0)
        self.assertEqual(normalize_tempo(220.0), 1.0)
        self.assertAlmostEqual(normalize_tempo(130.0), 0.5, delta=0.05)
        # Ngoai bien do
        self.assertEqual(normalize_tempo(20.0), 0.0)
        self.assertEqual(normalize_tempo(300.0), 1.0)

    def test_extract_track_vector_dimensions_and_ranges(self):
        vec = extract_track_vector(self.seed_track)
        self.assertEqual(len(vec), 5)
        for val in vec:
            self.assertTrue(0.0 <= val <= 1.0, f"Gia tri ngoai bien [0, 1]: {val}")

    def test_knn_song_recommendations_ranking(self):
        rec_data = get_song_recommendations(self.seed_track.spotify_id, top_k=2)
        
        self.assertIn('seed_track', rec_data)
        self.assertIn('recommendations', rec_data)
        recs = rec_data['recommendations']
        
        self.assertGreaterEqual(len(recs), 2)
        # Khong chua chinh seed track
        rec_ids = [r['spotify_id'] for r in recs]
        self.assertNotIn(self.seed_track.spotify_id, rec_ids)

        # Track tuong dong (trk_sim) phai co similarity cao hon track sôi dong (trk_dist)
        sim_scores = {r['spotify_id']: r['similarity_score'] for r in recs}
        self.assertGreater(sim_scores['trk_sim'], sim_scores['trk_dist'])

        # Kiem tra sap xep giam dan
        scores_list = [r['similarity_score'] for r in recs]
        self.assertEqual(scores_list, sorted(scores_list, reverse=True))

class AIPersonaGenerationTests(AIEngineBaseTestCase):
    """Kiem thu he thong sinh bao cao Persona va Heuristic Fallback."""

    def test_heuristic_persona_schema_and_mood_sum(self):
        ctx = extract_user_music_context(self.user, period_type='monthly')
        persona_data, provider = generate_heuristic_persona(ctx)

        self.assertIn('persona_title', persona_data)
        self.assertIn('tagline', persona_data)
        self.assertIn('vibe_summary', persona_data)
        self.assertIn('mood_distribution', persona_data)
        self.assertIn('ai_advice', persona_data)

        # Tong mood distribution phai bang 100%
        moods = persona_data['mood_distribution']
        self.assertEqual(sum(moods.values()), 100)

    def test_generate_and_save_persona_creates_db_record(self):
        persona_obj = generate_and_save_persona(self.user, period_type='monthly')
        
        self.assertIsInstance(persona_obj, AIMusicPersona)
        self.assertEqual(persona_obj.user, self.user)
        self.assertEqual(persona_obj.period_type, 'monthly')
        self.assertTrue(len(persona_obj.persona_title) > 0)
        self.assertEqual(sum(persona_obj.mood_distribution.values()), 100)

class AIApiEndpointsTests(AIEngineBaseTestCase):
    """Kiem thu cac REST API endpoints cua AI Engine."""

    def test_unauthenticated_request_rejected(self):
        self.client.logout()
        res = self.client.get('/api/ai/persona/latest/')
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_persona_generate_api(self):
        res = self.client.post('/api/ai/persona/generate/', {'period_type': 'weekly'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data['period_type'], 'weekly')
        self.assertIn('persona_title', data)
        self.assertIn('mood_distribution', data)

    def test_persona_latest_api(self):
        # Lan 1: chua co bao cao, he thong tu dong sinh moi
        res = self.client.get('/api/ai/persona/latest/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn('persona_title', data)

    def test_persona_history_api(self):
        generate_and_save_persona(self.user, 'weekly')
        generate_and_save_persona(self.user, 'monthly')
        
        res = self.client.get('/api/ai/persona/history/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        history = res.json()
        self.assertGreaterEqual(len(history), 2)

    def test_recommendations_api(self):
        res = self.client.get(f'/api/ai/recommendations/?track_id={self.seed_track.spotify_id}&top_k=2')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn('seed_track', data)
        self.assertIn('recommendations', data)
        self.assertEqual(len(data['recommendations']), 2)
