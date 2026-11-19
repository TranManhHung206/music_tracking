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

        from django.test import override_settings
        with override_settings(AI_PROVIDER='groq', GROQ_API_KEY='test-key', LLM_BASE_URL='', LLM_MODEL=''):
            with patch('ai_engine.services.facts_agent.agent._execute_groq_react_loop', side_effect=side_effect_exec):
                result = run_music_facts_agent(self.user, start_dt, now)
                self.assertIn('20b', result['agent_meta']['provider_used'])
                self.assertFalse(result['agent_meta']['is_fallback'])

    def test_cascading_all_fail_to_heuristic(self):
        from django.test import override_settings
        from ai_engine.services.facts_agent.agent import run_music_facts_agent
        from django.utils import timezone

        now = timezone.now()
        start_dt = now - timezone.timedelta(days=7)

        # Gia lap ca Tang 1 va Tang 2 deu that bai
        with override_settings(AI_PROVIDER='groq', GROQ_API_KEY='test-key', LLM_BASE_URL='', LLM_MODEL=''):
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


from django.test import TestCase as DjangoTestCase


class Phase1FactsSecurityAndTimezoneTests(DjangoTestCase):
    """Kiem thu loai bo search_codebase khoi facts_agent va localdate cho parse_period_to_bounds."""

    def tearDown(self):
        from django.utils import timezone
        timezone.deactivate()

    def test_search_codebase_not_exposed_in_facts_agent(self):
        from datetime import timedelta
        from django.utils import timezone
        from ai_engine.services.facts_agent.harness import (
            ALLOWED_TOOLS,
            GROQ_TOOL_DEFINITIONS,
            execute_agent_tool,
        )
        from django.contrib.auth.models import User

        self.assertNotIn("search_codebase", ALLOWED_TOOLS)
        tool_names = [t["function"]["name"] for t in GROQ_TOOL_DEFINITIONS]
        self.assertNotIn("search_codebase", tool_names)

        user = User.objects.create_user(username="facts_sec_user", password="pw")
        now = timezone.now()
        res = execute_agent_tool("search_codebase", {"query": "settings"}, user, now - timedelta(days=7), now)
        self.assertIn("error", res)

    def test_parse_period_to_bounds_respects_localdate(self):
        from unittest.mock import patch
        from datetime import datetime, timezone as dt_tz
        from zoneinfo import ZoneInfo
        from django.utils import timezone
        from ai_engine.services.facts_agent import parse_period_to_bounds

        # 2026-10-04 20:00Z = 2026-10-05 (+07, tuan moi) vs 2026-10-04 (-04, cuoi tuan cu)
        fixed_utc = datetime(2026, 10, 4, 20, 0, 0, tzinfo=dt_tz.utc)
        with patch("ai_engine.services.facts_agent.timezone.now", return_value=fixed_utc):
            timezone.activate(ZoneInfo("Asia/Ho_Chi_Minh"))
            s_vn, e_vn, label_vn = parse_period_to_bounds("week")
            self.assertIsNotNone(s_vn)
            self.assertEqual(timezone.localdate(s_vn).isoformat(), "2026-10-05")
            self.assertEqual(timezone.localdate(e_vn).isoformat(), "2026-10-11")
            self.assertTrue(len(label_vn) > 0)

            timezone.activate(ZoneInfo("America/New_York"))
            s_ny, e_ny, _ = parse_period_to_bounds("week")
            self.assertEqual(timezone.localdate(s_ny).isoformat(), "2026-09-28")
            self.assertEqual(timezone.localdate(e_ny).isoformat(), "2026-10-04")


class OpenAICompatibleLLMClientTests(DjangoTestCase):
    """Kiem thu client OpenAI-compatible (DeepSeek / Custom DNS) va dieu phoi da nha cung cap."""

    def test_url_normalization_and_provider_order(self):
        from django.test import override_settings
        from ai_engine.services.llm_client import (
            get_ai_provider_order,
            normalize_openai_chat_completions_url,
        )

        self.assertEqual(
            normalize_openai_chat_completions_url("api.deepseek.local"),
            "https://api.deepseek.local/v1/chat/completions",
        )
        self.assertEqual(
            normalize_openai_chat_completions_url("https://api.deepseek.local/v1/"),
            "https://api.deepseek.local/v1/chat/completions",
        )
        self.assertEqual(
            normalize_openai_chat_completions_url("localhost:11434/v1"),
            "http://localhost:11434/v1/chat/completions",
        )
        self.assertEqual(
            normalize_openai_chat_completions_url("https://gw.example.com/custom/v1/chat/completions"),
            "https://gw.example.com/custom/v1/chat/completions",
        )

        with override_settings(AI_PROVIDER="openai_compatible"):
            self.assertEqual(get_ai_provider_order()[0], "openai_compatible")
        with override_settings(AI_PROVIDER="deepseek"):
            self.assertEqual(get_ai_provider_order()[0], "openai_compatible")
        with override_settings(AI_PROVIDER="gemini"):
            self.assertEqual(get_ai_provider_order()[0], "gemini")

    def test_extract_json_object_strips_think_blocks_and_fences(self):
        from ai_engine.services.llm_client import extract_json_object, strip_reasoning_blocks

        raw = "<think>\nSuy luan noi bo...\n</think>\n```json\n{\"persona_title\": \"Night Owl\", \"tagline\": \"chill\"}\n```"
        self.assertNotIn("<think>", strip_reasoning_blocks(raw))
        parsed = extract_json_object(raw)
        self.assertEqual(parsed["persona_title"], "Night Owl")

    def test_openai_compatible_client_retries_without_response_format_on_400(self):
        from unittest.mock import MagicMock, patch
        from ai_engine.services.llm_client import OpenAICompatibleClient, OpenAICompatibleConfig

        cfg = OpenAICompatibleConfig(
            base_url="api.deepseek-test.local",
            api_key="test-key-xyz",
            model="deepseek-v4.1",
            timeout_seconds=15.0,
        )
        client = OpenAICompatibleClient(cfg)

        resp_400 = MagicMock(status_code=400)
        resp_200 = MagicMock(status_code=200)
        resp_200.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "<think>ok</think>{\"ok\": true}"}}]
        }

        captured_payloads = []

        def fake_post(url, headers=None, json=None):
            captured_payloads.append((url, headers, dict(json or {})))
            return resp_400 if len(captured_payloads) == 1 else resp_200

        with patch("ai_engine.services.llm_client.httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.post.side_effect = fake_post
            msg = client.create_chat_completion(
                model="deepseek-v4.1",
                messages=[{"role": "user", "content": "hi"}],
                response_format={"type": "json_object"},
            )

        self.assertEqual(len(captured_payloads), 2)
        self.assertEqual(captured_payloads[0][0], "https://api.deepseek-test.local/v1/chat/completions")
        self.assertEqual(captured_payloads[0][1]["Authorization"], "Bearer test-key-xyz")
        self.assertIn("response_format", captured_payloads[0][2])
        self.assertNotIn("response_format", captured_payloads[1][2])
        self.assertIn('"ok": true', msg.content)

    def test_all_four_ai_modules_use_openai_compatible_when_configured(self):
        from datetime import timedelta
        from unittest.mock import MagicMock, patch
        from django.contrib.auth.models import User
        from django.test import override_settings
        from django.utils import timezone
        from tracker.models import ListeningHistory, Track
        from ai_engine.services.ai_persona import generate_and_save_persona
        from ai_engine.services.facts_agent.agent import run_music_facts_agent
        from ai_engine.services.rag.service import CodebaseRAGService
        from ai_engine.services.assistant.service import HybridAssistantService

        user = User.objects.create_user(username="deepseek_user", password="pw")
        trk = Track.objects.create(spotify_id="ds_trk_1", name="Test Track", duration_ms=180000)
        now = timezone.now()
        ListeningHistory.objects.create(user=user, track=trk, played_at=now - timedelta(minutes=5))

        env_overrides = {
            "AI_PROVIDER": "openai_compatible",
            "LLM_BASE_URL": "https://deepseek.internal.example/v1",
            "LLM_API_KEY": "secret-token-sample",
            "LLM_MODEL": "deepseek-v4.1",
            "GROQ_API_KEY": "",
            "GEMINI_API_KEY": "",
        }

        persona_json = (
            '{"persona_title": "DeepSeek Explorer", "tagline": "Nghe nhac khong gioi han.", '
            '"vibe_summary": "Ban nghe deu dan.", "mood_distribution": {"energetic": 50, "melancholic": 20, "focused": 30}, '
            '"recommended_listening_time": "21:00 - 23:00", "ai_advice": "Hay tiep tuc kham pha."}'
        )
        facts_json = (
            '{"facts": ['
            '{"id": "f1", "category": "repeat_loop", "badge": "Loop", "title": "Bai hat yeu thich", '
            '"description": "Ban da phat bai nay nhieu lan.", "metric_highlight": "1 lan", "evidence": "Test Track"},'
            '{"id": "f2", "category": "night_owl", "badge": "Dem", "title": "Khung gio dem", '
            '"description": "Ban hay nghe nhac luc toi muon.", "metric_highlight": "21h", "evidence": "Test Track"},'
            '{"id": "f3", "category": "contrast", "badge": "Vibe", "title": "Da sac thai", '
            '"description": "Ban chuyen doi nhip dieu linh hoat.", "metric_highlight": "100%", "evidence": "Test Track"}'
            ']}'
        )

        with override_settings(**env_overrides):
            # 1. AI Music Persona
            with patch("ai_engine.services.llm_client.OpenAICompatibleClient._post_payload") as mock_post:
                mock_post.return_value = MagicMock(
                    status_code=200,
                    json=lambda: {"choices": [{"message": {"role": "assistant", "content": persona_json}}]},
                )
                persona = generate_and_save_persona(user, period_type="monthly")
            self.assertEqual(persona.provider_used, "openai_compatible")
            self.assertEqual(persona.model_name, "deepseek-v4.1")

            # 2. Aura Music Detective (ReAct tool call -> JSON synthesis)
            tool_resp = MagicMock(
                status_code=200,
                json=lambda: {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {"name": "query_repeat_loops", "arguments": "{}"},
                                    }
                                ],
                            }
                        }
                    ]
                },
            )
            final_facts_resp = MagicMock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"role": "assistant", "content": facts_json}}]},
            )
            with patch("ai_engine.services.llm_client.OpenAICompatibleClient._post_payload", side_effect=[tool_resp, final_facts_resp]):
                facts_res = run_music_facts_agent(user, now - timedelta(days=7), now)
            self.assertEqual(facts_res["agent_meta"]["provider_used"], "openai_compatible:deepseek-v4.1")
            self.assertEqual(facts_res["agent_meta"]["model_name"], "deepseek-v4.1")
            self.assertFalse(facts_res["agent_meta"]["is_fallback"])

            # 3. Codebase / Website RAG _generate_answer
            rag_svc = CodebaseRAGService()
            with patch("ai_engine.services.llm_client.OpenAICompatibleClient._post_payload") as mock_post:
                mock_post.return_value = MagicMock(
                    status_code=200,
                    json=lambda: {"choices": [{"message": {"role": "assistant", "content": "<think>plan</think>Tra loi tu DeepSeek [S1]."}}]},
                )
                rag_ans = rag_svc._generate_answer([{"role": "user", "content": "test"}])
            self.assertEqual(rag_ans, "Tra loi tu DeepSeek [S1].")

            # 4. Hybrid Assistant Music Insights
            assistant_svc = HybridAssistantService()
            with patch("ai_engine.services.llm_client.OpenAICompatibleClient._post_payload") as mock_post:
                mock_post.return_value = MagicMock(
                    status_code=200,
                    json=lambda: {"choices": [{"message": {"role": "assistant", "content": "Ban co 1 luot phat trong ky."}}]},
                )
                txt, prov, mod = assistant_svc._synthesize_music_with_llm(
                    "Tong ket tuan nay",
                    {"summary": {"total_plays": 1}},
                    [],
                )
            self.assertEqual(prov, "openai_compatible")
            self.assertEqual(mod, "deepseek-v4.1")
            self.assertIn("1 luot phat", txt)




