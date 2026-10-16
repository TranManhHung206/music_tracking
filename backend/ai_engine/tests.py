"""
Unit tests cho app ai_engine.
Kiem tra model AIMusicPersona, Vectorization am thanh, KNN Recommender va cac AI API Endpoints.
"""

import json
from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from tracker.models import Artist, Album, Track, ListeningHistory
from ai_engine.models import AIMusicPersona
from ai_engine.services.knn_recommender import (
    normalize_tempo,
    extract_track_vector,
    apply_feature_weights,
    get_song_recommendations,
    FEATURE_WEIGHTS,
    MAX_WEIGHTED_DISTANCE,
)
from ai_engine.services.ai_persona import (
    generate_heuristic_persona,
    extract_user_music_context,
    generate_and_save_persona,
)

class AIEngineBaseTestCase(APITestCase):
    """Lop co so thiet lap du lieu kiem thu cho AI Engine."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
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

    def test_apply_feature_weights(self):
        raw_vec = [1.0, 1.0, 1.0, 1.0, 1.0]
        weighted = apply_feature_weights(raw_vec)
        self.assertEqual(len(weighted), 5)
        # Kiem tra trong so sqrt(w)
        import numpy as np
        expected = np.sqrt(FEATURE_WEIGHTS)
        np.testing.assert_allclose(weighted, expected, rtol=1e-5)

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

    def test_knn_song_recommendations_deduplication(self):
        # Tao them ban sao cua trk_sim voi cung ten va ca si nhung khac spotify_id
        duplicate_track = Track.objects.create(
            spotify_id='trk_sim_duplicate',
            name='Ngày Chưa Giông Bão',
            album=self.album,
            duration_ms=231000,
            danceability=0.42,
            energy=0.35,
            valence=0.28,
            acousticness=0.80,
            tempo=88.0,
            features_synced=True,
        )
        duplicate_track.artists.add(self.artist)

        rec_data = get_song_recommendations(self.seed_track.spotify_id, top_k=5)
        recs = rec_data['recommendations']
        names = [r['name'] for r in recs]
        # Ten bai hat phai la duy nhat trong ket qua tra ve
        self.assertEqual(len(names), len(set(names)))

MOCK_PERSONA_INFERENCE = (
    {
        "persona_title": "The Late-Night Sonic Rebel",
        "tagline": "Đêm khuya, năng lượng bùng nổ và chiều sâu nội tâm.",
        "vibe_summary": "Bạn thường nghe nhạc đêm muộn với gu acoustic và rock.",
        "mood_distribution": {"energetic": 40, "melancholic": 30, "focused": 30},
        "recommended_listening_time": "22:00 - 02:00",
        "ai_advice": "Duy trì năng lượng tích cực này!",
    },
    "groq:openai/gpt-oss-20b"
)

MOCK_FACTS_AGENT_RESULT = {
    "facts": [
        {
            "id": "fact-1",
            "category": "repeat_loop",
            "badge": "Vòng Lặp Vô Tận",
            "title": "Cơn Nghiện Nhạc",
            "description": "Bạn đã nghe bài hát liên tục.",
            "metric_highlight": "5 lần",
            "evidence": "Có Chàng Trai Viết Lên Cây",
        }
    ],
    "agent_meta": {
        "agent_name": "Aura Music Detective",
        "provider_used": "groq:openai/gpt-oss-20b",
        "model_name": "openai/gpt-oss-20b",
        "iterations_used": 1,
        "tools_called": ["query_repeat_loops"],
        "is_fallback": False,
    }
}

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

    @patch('ai_engine.services.ai_persona.call_groq_inference', return_value=MOCK_PERSONA_INFERENCE)
    def test_generate_and_save_persona_creates_db_record(self, mock_groq):
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

    @patch('ai_engine.services.ai_persona.call_groq_inference', return_value=MOCK_PERSONA_INFERENCE)
    def test_persona_generate_api(self, mock_groq):
        res = self.client.post('/api/ai/persona/generate/', {'period_type': 'weekly'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data['period_type'], 'weekly')
        self.assertIn('persona_title', data)
        self.assertIn('mood_distribution', data)

    @patch('ai_engine.services.ai_persona.call_groq_inference', return_value=MOCK_PERSONA_INFERENCE)
    def test_persona_latest_api(self, mock_groq):
        # Lan 1: chua co bao cao, he thong tra ve {} (khong tu dong tao ton token)
        res = self.client.get('/api/ai/persona/latest/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json(), {})

        # Lan 2: Sau khi nguoi dung da chu dong tao persona
        generate_and_save_persona(self.user, 'monthly')
        res2 = self.client.get('/api/ai/persona/latest/')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        data = res2.json()
        self.assertIn('persona_title', data)

    @patch('ai_engine.services.ai_persona.call_groq_inference', return_value=MOCK_PERSONA_INFERENCE)
    def test_persona_history_api(self, mock_groq):
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

    def test_music_facts_preview_mode_without_trigger(self):
        from django.utils import timezone
        now = timezone.now()
        for i in range(4):
            ListeningHistory.objects.create(
                user=self.user,
                track=self.seed_track,
                played_at=now - timezone.timedelta(minutes=10 * i),
            )

        # Duyet thong thuong (khong truyen trigger=true): Dung che do preview noi bo, 0 token AI
        res = self.client.get('/api/ai/facts/?period=week')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn('facts', data)
        self.assertIn('agent_meta', data)
        self.assertEqual(data['agent_meta']['provider_used'], 'db-analytics-preview')

    @patch('ai_engine.services.facts_agent.agent._execute_groq_react_loop', return_value=MOCK_FACTS_AGENT_RESULT)
    def test_music_facts_manual_trigger(self, mock_react):
        from django.utils import timezone
        now = timezone.now()
        for i in range(4):
            ListeningHistory.objects.create(
                user=self.user,
                track=self.seed_track,
                played_at=now - timezone.timedelta(minutes=10 * i),
            )

        # Kich hoat thu cong qua trigger=true
        res = self.client.get('/api/ai/facts/?period=week&trigger=true')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn('facts', data)
        self.assertIn('agent_meta', data)
        self.assertGreater(len(data['facts']), 0)

    def test_cascading_primary_to_backup_model(self):
        from ai_engine.services.facts_agent.agent import run_music_facts_agent
        from django.utils import timezone

        now = timezone.now()
        start_dt = now - timezone.timedelta(days=7)

        # Gia lap Tang 1 (120B) bi loi / rate limit, Tang 2 (20B) thanh cong
        mock_facts = [{
            "id": "fact-1",
            "category": "repeat_loop",
            "badge": "Vòng Lặp Vô Tận",
            "title": "Cơn Nghiện Nhạc",
            "description": "Bạn đã nghe bài hát liên tục.",
            "metric_highlight": "5 lần",
            "evidence": "Bài hát mẫu",
        }]

        def side_effect_exec(client, model_name, user, start_dt, end_dt, period_label):
            if '120b' in model_name:
                return None
            return {
                "facts": mock_facts,
                "agent_meta": {
                    "agent_name": "Aura Music Detective",
                    "provider_used": f"groq:{model_name}",
                    "model_name": model_name,
                    "iterations_used": 1,
                    "tools_called": ["query_repeat_loops"],
                    "is_fallback": False,
                }
            }

        with patch('ai_engine.services.facts_agent.agent._execute_groq_react_loop', side_effect=side_effect_exec):
            result = run_music_facts_agent(self.user, start_dt, now)
            self.assertIn('20b', result['agent_meta']['provider_used'])
            self.assertFalse(result['agent_meta']['is_fallback'])

    def test_cascading_all_fail_to_heuristic(self):
        from ai_engine.services.facts_agent.agent import run_music_facts_agent
        from django.utils import timezone

        now = timezone.now()
        start_dt = now - timezone.timedelta(days=7)

        # Gia lap ca Tang 1 va Tang 2 deu that bai
        with patch('ai_engine.services.facts_agent.agent._execute_groq_react_loop', return_value=None):
            result = run_music_facts_agent(self.user, start_dt, now)
            self.assertEqual(result['agent_meta']['provider_used'], 'heuristic-fallback')
            self.assertTrue(result['agent_meta']['is_fallback'])

    def test_music_facts_unauthenticated_rejected(self):
        self.client.logout()
        res = self.client.get('/api/ai/facts/?period=week')
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_execute_groq_react_loop_multi_tool_synthesis(self):
        from unittest.mock import MagicMock
        from ai_engine.services.facts_agent.agent import _execute_groq_react_loop
        from django.utils import timezone

        mock_client = MagicMock()
        recorded_calls = []

        def mock_create(**kwargs):
            recorded_calls.append(kwargs)
            call_count = len(recorded_calls)
            mock_choice = MagicMock()

            if call_count == 1:
                # Turn 1: Goi tool query_repeat_loops
                mock_tool = MagicMock()
                mock_tool.id = "call_1"
                mock_tool.function.name = "query_repeat_loops"
                mock_tool.function.arguments = json.dumps({"min_repeats": 3})
                mock_choice.message.tool_calls = [mock_tool]
                mock_choice.message.content = None
            elif call_count == 2:
                # Turn 2: Goi tool query_night_owl_anomaly
                mock_tool = MagicMock()
                mock_tool.id = "call_2"
                mock_tool.function.name = "query_night_owl_anomaly"
                mock_tool.function.arguments = "{}"
                mock_choice.message.tool_calls = [mock_tool]
                mock_choice.message.content = None
            elif call_count == 3:
                # Turn 3: Goi tool query_marathon_sessions
                mock_tool = MagicMock()
                mock_tool.id = "call_3"
                mock_tool.function.name = "query_marathon_sessions"
                mock_tool.function.arguments = "{}"
                mock_choice.message.tool_calls = [mock_tool]
                mock_choice.message.content = None
            else:
                # Turn 4: Ep tong hop (tool_choice="none"), xuat Strict JSON
                mock_choice.message.tool_calls = None
                mock_choice.message.content = json.dumps({
                    "facts": [
                        {
                            "id": "fact-1",
                            "category": "repeat_loop",
                            "badge": "Vong Lap Vo Tan",
                            "title": "Nghien Nhac",
                            "description": "Ban da nghe 10 lan.",
                            "metric_highlight": "10 lan",
                            "evidence": "Song A",
                        },
                        {
                            "id": "fact-2",
                            "category": "night_owl",
                            "badge": "Cu Dem",
                            "title": "Am Nhac Ve Dem",
                            "description": "Ban thuong nghe luc 2h sang.",
                            "metric_highlight": "80%",
                            "evidence": "Song B",
                        },
                        {
                            "id": "fact-3",
                            "category": "marathon",
                            "badge": "Chay Dua",
                            "title": "Phien Nghe Bat Tan",
                            "description": "Ban da nghe lien tuc 4 tieng.",
                            "metric_highlight": "4 tieng",
                            "evidence": "Song C",
                        }
                    ]
                })

            mock_resp = MagicMock()
            mock_resp.choices = [mock_choice]
            return mock_resp

        mock_client.chat.completions.create.side_effect = mock_create

        now = timezone.now()
        start_dt = now - timezone.timedelta(days=7)

        result = _execute_groq_react_loop(
            client=mock_client,
            model_name="openai/gpt-oss-120b",
            user=self.user,
            start_dt=start_dt,
            end_dt=now,
            period_label="tuan nay",
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(result["facts"]), 3)
        self.assertFalse(result["agent_meta"]["is_fallback"])
        self.assertEqual(result["agent_meta"]["iterations_used"], 4)
        # Kiem tra luot thu 4 phai duoc ep tong hop voi tool_choice="none"
        self.assertEqual(recorded_calls[3]["tool_choice"], "none")
        self.assertEqual(recorded_calls[3]["response_format"], {"type": "json_object"})

    def test_investigation_leads_and_tool_definitions_integrity(self):
        from ai_engine.services.facts_agent.agent import INVESTIGATION_LEADS
        from ai_engine.services.facts_agent.harness import GROQ_TOOL_DEFINITIONS, ALLOWED_TOOLS

        self.assertGreaterEqual(len(INVESTIGATION_LEADS), 4)
        tool_names = [t["function"]["name"] for t in GROQ_TOOL_DEFINITIONS]
        self.assertEqual(set(tool_names), set(ALLOWED_TOOLS.keys()))

    def test_heuristic_facts_randomized_diversity(self):
        from django.utils import timezone
        from ai_engine.services.facts_agent.harness import generate_heuristic_facts

        now = timezone.now()
        start_dt = now - timezone.timedelta(days=7)

        # Tao 4 bai hat va nghe de thoa man ca 4 loai facts: repeat_loop, artist_dominance, marathon, night_owl
        for i in range(5):
            # Nghe lap di lap lai de thoa man repeat_loop
            ListeningHistory.objects.create(
                user=self.user,
                track=self.seed_track,
                played_at=now - timezone.timedelta(hours=1, minutes=10 * i),
            )

        for i in range(4):
            # Nghe vao ban dem 02:00 de thoa man night_owl
            night_dt = (now - timezone.timedelta(days=1)).replace(hour=2, minute=10 + i * 5)
            ListeningHistory.objects.create(
                user=self.user,
                track=self.seed_track,
                played_at=night_dt,
            )

        # Chay 10 lan generate_heuristic_facts va kiem tra tinh hop le
        all_returned_categories = set()
        for _ in range(10):
            facts = generate_heuristic_facts(self.user, start_dt, now)
            self.assertEqual(len(facts), 3)
            for f in facts:
                self.assertIn("category", f)
                self.assertIn("title", f)
                self.assertIn("description", f)
                all_returned_categories.add(f["category"])

        # Phai xuat hien tu 2 categories tro len, chung to he thong co chon loc da dang
        self.assertGreater(len(all_returned_categories), 1)



