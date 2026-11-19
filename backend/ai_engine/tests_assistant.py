"""
Unit & Integration tests toan dien cho Hybrid Music & Website Assistant (Phase 4).
Kiem thu phan quyen User A/B, is_staff redaction, intent routing, grounding, provenance va fallback.
"""

from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from tracker.models import Album, Artist, ListeningHistory, Track
from ai_engine.services.rag.schemas import CitationItem, RAGQueryResponse
from ai_engine.services.rag.service import CodebaseRAGService
from ai_engine.services.assistant.session_store import get_session_state

User = get_user_model()


class HybridAssistantTestCase(TestCase):
    """Bo kiem thu Phase 4 cho endpoint /api/ai/assistant/query/ va session isolation."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user_a = User.objects.create_user(username="listener_a", password="pass_a_123")
        self.user_b = User.objects.create_user(username="listener_b", password="pass_b_123")
        self.staff_user = User.objects.create_user(
            username="staff_admin", password="pass_admin_123", is_staff=True
        )

        self.artist_a = Artist.objects.create(spotify_id="art_alpha", name="Artist Alpha")
        self.album_a = Album.objects.create(spotify_id="alb_alpha", name="Album Alpha", image_url="")
        self.album_a.artists.add(self.artist_a)
        self.track_a = Track.objects.create(
            spotify_id="trk_alpha_01",
            name="User A Secret Anthem",
            duration_ms=210000,
            album=self.album_a,
            danceability=0.72,
            energy=0.81,
            valence=0.64,
            acousticness=0.18,
            tempo=124.0,
            features_synced=True,
            features_source="estimated",
        )
        self.track_a.artists.add(self.artist_a)

        self.track_a2 = Track.objects.create(
            spotify_id="trk_alpha_02",
            name="Night Horizon Mix",
            duration_ms=195000,
            album=self.album_a,
            danceability=0.70,
            energy=0.79,
            valence=0.60,
            acousticness=0.20,
            tempo=122.0,
            features_synced=True,
            features_source="spotify",
        )
        self.track_a2.artists.add(self.artist_a)

        self.artist_b = Artist.objects.create(spotify_id="art_beta", name="Artist Beta")
        self.album_b = Album.objects.create(spotify_id="alb_beta", name="Album Beta", image_url="")
        self.album_b.artists.add(self.artist_b)
        self.track_b = Track.objects.create(
            spotify_id="trk_beta_01",
            name="User B Private Track",
            duration_ms=180000,
            album=self.album_b,
            danceability=0.40,
            energy=0.35,
            valence=0.25,
            acousticness=0.75,
            tempo=88.0,
            features_synced=True,
            features_source="spotify",
        )
        self.track_b.artists.add(self.artist_b)

        now = timezone.now()
        for i in range(4):
            ListeningHistory.objects.create(
                user=self.user_a,
                track=self.track_a,
                played_at=now - timedelta(hours=i + 1),
            )
        ListeningHistory.objects.create(
            user=self.user_a,
            track=self.track_a2,
            played_at=now - timedelta(days=8),
        )
        ListeningHistory.objects.create(
            user=self.user_b,
            track=self.track_b,
            played_at=now - timedelta(hours=2),
        )

    def test_unauthenticated_rejected(self):
        res_query = self.client.post(
            "/api/ai/assistant/query/",
            {"query": "Tuần này tôi nghe gì?"},
            format="json",
        )
        res_clear = self.client.post(
            "/api/ai/assistant/session/clear/",
            {"session_id": "s1"},
            format="json",
        )
        self.assertEqual(res_query.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res_clear.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_scope_and_session_isolation(self):
        self.client.force_authenticate(user=self.user_a)
        with self.settings(
            GROQ_API_KEY="",
            GEMINI_API_KEY="",
            LLM_BASE_URL="",
            LLM_API_KEY="",
            LLM_MODEL="",
        ):
            with patch.dict(
                "os.environ",
                {
                    "GROQ_API_KEY": "",
                    "GEMINI_API_KEY": "",
                    "LLM_BASE_URL": "",
                    "LLM_API_KEY": "",
                    "LLM_MODEL": "",
                    "OPENAI_BASE_URL": "",
                    "OPENAI_API_KEY": "",
                },
                clear=False,
            ):
                res_a = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Tuần này tôi nghe bài hát nào nhiều nhất?",
                        "mode": "music_insights",
                        "session_id": "shared_sid_1",
                        "user_id": self.user_b.id,
                    },
                    format="json",
                )
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        data_a = res_a.json()
        self.assertEqual(data_a["resolved_domain"], "music_insights")
        self.assertIn("User A Secret Anthem", data_a["answer"])
        self.assertNotIn("User B Private Track", data_a["answer"])
        self.assertNotIn("Artist Beta", data_a["answer"])

        # User B dung chung session_id nhung phai bi co lap hoan toan
        self.client.force_authenticate(user=self.user_b)
        with self.settings(
            GROQ_API_KEY="",
            GEMINI_API_KEY="",
            LLM_BASE_URL="",
            LLM_API_KEY="",
            LLM_MODEL="",
        ):
            with patch.dict(
                "os.environ",
                {
                    "GROQ_API_KEY": "",
                    "GEMINI_API_KEY": "",
                    "LLM_BASE_URL": "",
                    "LLM_API_KEY": "",
                    "LLM_MODEL": "",
                    "OPENAI_BASE_URL": "",
                    "OPENAI_API_KEY": "",
                },
                clear=False,
            ):
                res_b = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Top bài hát của tôi tuần này?",
                        "mode": "music_insights",
                        "session_id": "shared_sid_1",
                    },
                    format="json",
                )
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        data_b = res_b.json()
        self.assertIn("User B Private Track", data_b["answer"])
        self.assertNotIn("User A Secret Anthem", data_b["answer"])
        self.assertEqual(data_b["meta"]["session_turns"], 1)

    def test_music_question_routes_without_codebase_rag(self):
        self.client.force_authenticate(user=self.user_a)
        with patch.object(CodebaseRAGService, "query") as mock_rag:
            with self.settings(
                GROQ_API_KEY="",
                GEMINI_API_KEY="",
                LLM_BASE_URL="",
                LLM_API_KEY="",
                LLM_MODEL="",
            ):
                with patch.dict(
                    "os.environ",
                    {
                        "GROQ_API_KEY": "",
                        "GEMINI_API_KEY": "",
                        "LLM_BASE_URL": "",
                        "LLM_API_KEY": "",
                        "LLM_MODEL": "",
                        "OPENAI_BASE_URL": "",
                        "OPENAI_API_KEY": "",
                    },
                    clear=False,
                ):
                    res = self.client.post(
                        "/api/ai/assistant/query/",
                        {"query": "Audio features của tôi tuần này ra sao?", "mode": "auto"},
                        format="json",
                    )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_rag.assert_not_called()
        payload = res.json()
        self.assertEqual(payload["resolved_domain"], "music_insights")
        self.assertTrue(any(ev.get("is_estimate") for ev in payload["evidence"]))

    def test_website_question_routes_and_redacts_for_regular_user(self):
        fake_rag = RAGQueryResponse(
            query="Cơ chế bảo mật token",
            answer="Hệ thống khóa kín token bằng Fernet AES [S1]. Tham khảo `backend/users/services/encryption.py`.",
            citations=[
                CitationItem(
                    citation_id="S1",
                    file_path="backend/users/services/encryption.py",
                    line_start=1,
                    line_end=20,
                    symbol="encrypt_token",
                    snippet="def encrypt_token(raw): ...",
                )
            ],
            verification={"is_escape_hatch": False, "all_valid": True, "citation_existence_rate": 1.0},
            latency_ms=42.5,
            retrieved_chunks_count=3,
        )

        self.client.force_authenticate(user=self.user_a)
        with patch.object(CodebaseRAGService, "query", return_value=fake_rag) as mock_rag:
            res_regular = self.client.post(
                "/api/ai/assistant/query/",
                {
                    "query": "Thông tin tài khoản Spotify và token của tôi được bảo vệ thế nào?",
                    "mode": "auto",
                    "rag_mode": "baseline_dense",
                },
                format="json",
            )
        self.assertEqual(res_regular.status_code, status.HTTP_200_OK)
        # Non-staff phai bi ep ve full_cascade
        self.assertEqual(mock_rag.call_args.kwargs["mode"].value, "full_cascade")
        reg_data = res_regular.json()
        self.assertEqual(reg_data["resolved_domain"], "website_support")
        self.assertNotIn("[S1]", reg_data["answer"])
        self.assertNotIn("backend/users/services/encryption.py", reg_data["answer"])
        self.assertEqual(reg_data["dev_citations"], [])
        self.assertIsNone(reg_data["dev_metrics"])
        self.assertEqual(reg_data["topics"][0]["title"], "Xác thực Spotify & Bảo mật tài khoản")

        # Staff user xem duoc dev citations va metrics
        self.client.force_authenticate(user=self.staff_user)
        with patch.object(CodebaseRAGService, "query", return_value=fake_rag) as mock_rag_staff:
            res_staff = self.client.post(
                "/api/ai/assistant/query/",
                {
                    "query": "Cơ chế mã hóa Fernet hoạt động sao?",
                    "mode": "website_support",
                    "rag_mode": "baseline_dense",
                },
                format="json",
            )
        self.assertEqual(res_staff.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_rag_staff.call_args.kwargs["mode"].value, "baseline_dense")
        staff_data = res_staff.json()
        self.assertEqual(len(staff_data["dev_citations"]), 1)
        self.assertEqual(staff_data["dev_citations"][0]["file_path"], "backend/users/services/encryption.py")
        self.assertIsNotNone(staff_data["dev_metrics"])

    def test_ambiguous_query_returns_clarification_without_calling_domains(self):
        self.client.force_authenticate(user=self.user_a)
        with patch.object(CodebaseRAGService, "query") as mock_rag:
            res = self.client.post(
                "/api/ai/assistant/query/",
                {"query": "Giải thích giúp tôi", "mode": "auto"},
                format="json",
            )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_rag.assert_not_called()
        data = res.json()
        self.assertTrue(data["needs_clarification"])
        self.assertEqual(data["resolved_domain"], "clarification")
        self.assertEqual(len(data["clarification_options"]), 2)

    def test_out_of_scope_trivia_in_music_mode_does_not_fabricate_stats(self):
        self.client.force_authenticate(user=self.user_a)
        res = self.client.post(
            "/api/ai/assistant/query/",
            {"query": "Thời tiết Hà Nội hôm nay bao nhiêu độ?", "mode": "music_insights"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["evidence"], [])
        self.assertIn("ngoài phạm vi", data["answer"].lower())

    def test_period_scope_respects_dashboard_vs_requested_period(self):
        self.client.force_authenticate(user=self.user_a)
        with self.settings(
            GROQ_API_KEY="",
            GEMINI_API_KEY="",
            LLM_BASE_URL="",
            LLM_API_KEY="",
            LLM_MODEL="",
        ):
            with patch.dict(
                "os.environ",
                {
                    "GROQ_API_KEY": "",
                    "GEMINI_API_KEY": "",
                    "LLM_BASE_URL": "",
                    "LLM_API_KEY": "",
                    "LLM_MODEL": "",
                    "OPENAI_BASE_URL": "",
                    "OPENAI_API_KEY": "",
                },
                clear=False,
            ):
                # 1. Theo ky dang chon tren Dashboard
                res_dash = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Tổng kết gu nghe nhạc của tôi",
                        "mode": "music_insights",
                        "period_context": {
                            "period_type": "month",
                            "start_date": "2020-01-01",
                            "end_date": "2020-01-31",
                            "label": "Tháng 01/2020",
                        },
                    },
                    format="json",
                )
                self.assertEqual(res_dash.status_code, status.HTTP_200_OK)
                self.assertEqual(res_dash.json()["scope"]["source"], "dashboard_period")
                self.assertEqual(res_dash.json()["scope"]["label"], "Tháng 01/2020")
                self.assertIn("0 lượt phát", res_dash.json()["answer"])

                # 2. Ky yeu cau truc tiep trong cau hoi uu tien cao hon Dashboard
                res_req = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Tuần trước tôi đã nghe những bài nào?",
                        "mode": "music_insights",
                        "period_context": {
                            "period_type": "month",
                            "start_date": "2020-01-01",
                            "end_date": "2020-01-31",
                            "label": "Tháng 01/2020",
                        },
                    },
                    format="json",
                )
                self.assertEqual(res_req.status_code, status.HTTP_200_OK)
                self.assertEqual(res_req.json()["scope"]["source"], "requested_in_query")
                self.assertIn("Night Horizon Mix", res_req.json()["answer"])

    def test_provider_failure_graceful_fallback_and_session_clear(self):
        self.client.force_authenticate(user=self.user_a)
        with patch.object(CodebaseRAGService, "query", side_effect=RuntimeError("RAG timeout")):
            res_ws_err = self.client.post(
                "/api/ai/assistant/query/",
                {
                    "query": "Hệ thống dùng công nghệ đồng bộ thế nào?",
                    "mode": "website_support",
                    "session_id": "clean_sid",
                },
                format="json",
            )
        self.assertEqual(res_ws_err.status_code, status.HTTP_200_OK)
        self.assertTrue(res_ws_err.json()["meta"]["is_fallback"])
        self.assertIn("gián đoạn", res_ws_err.json()["answer"].lower())

        # Kiem tra tách biệt domain trong session store va xoa session
        with self.settings(
            GROQ_API_KEY="",
            GEMINI_API_KEY="",
            LLM_BASE_URL="",
            LLM_API_KEY="",
            LLM_MODEL="",
        ):
            with patch.dict(
                "os.environ",
                {
                    "GROQ_API_KEY": "",
                    "GEMINI_API_KEY": "",
                    "LLM_BASE_URL": "",
                    "LLM_API_KEY": "",
                    "LLM_MODEL": "",
                    "OPENAI_BASE_URL": "",
                    "OPENAI_API_KEY": "",
                },
                clear=False,
            ):
                self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Gợi ý cho tôi bài giống User A Secret Anthem",
                        "mode": "music_insights",
                        "session_id": "clean_sid",
                    },
                    format="json",
                )

        state = get_session_state(self.user_a.id, "clean_sid")
        self.assertEqual(len(state["website_turns"]), 1)
        self.assertEqual(len(state["music_turns"]), 1)

        res_clear = self.client.post(
            "/api/ai/assistant/session/clear/",
            {"session_id": "clean_sid"},
            format="json",
        )
        self.assertEqual(res_clear.status_code, status.HTTP_200_OK)
        cleared_state = get_session_state(self.user_a.id, "clean_sid")
        self.assertEqual(cleared_state["website_turns"], [])
        self.assertEqual(cleared_state["music_turns"], [])
