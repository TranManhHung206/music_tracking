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
from ai_engine.services.assistant.session_store import get_domain_context, get_session_state
from ai_engine.services.assistant.artist_tools import (
    extract_date_range_from_text,
    tool_artist_listening_habits,
    tool_artist_listening_overview,
    tool_artist_period_comparison,
    tool_artist_top_tracks,
)
from ai_engine.services.assistant.genre_tools import (
    tool_genre_listening_overview,
    tool_genre_top_artists,
    tool_genre_top_tracks,
)
from ai_engine.services.assistant.memory_tools import (
    extract_and_strip_memory_ops,
    tool_update_session_memory,
)
from ai_engine.services.assistant.service import HybridAssistantService, _sanitize_music_answer

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
        self.assertEqual(cleared_state["music_memory"], "")
        self.assertEqual(cleared_state["music_entities"], {})

    def test_selective_tool_calling_and_relevant_evidence_for_top_artist(self):
        """Hoi top nghe si chi goi top_artists va chi sinh Evidence nghe si, khong dinh kem the loai/so sanh thua."""
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
                res = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "nghệ sĩ nào tui nghe nhiều nhất năm nay",
                        "mode": "auto",
                        "session_id": "sel_artist_sid",
                    },
                    format="json",
                )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["resolved_domain"], "music_insights")
        self.assertEqual(data["meta"]["tools_used"], ["top_artists"])
        self.assertNotIn("genre_distribution", data["meta"]["tools_used"])
        self.assertNotIn("period_comparison", data["meta"]["tools_used"])
        self.assertNotIn("top_tracks", data["meta"]["tools_used"])

        ev_labels = [ev["label"] for ev in data["evidence"]]
        self.assertEqual(ev_labels, ["Nghệ sĩ dẫn đầu"])
        self.assertEqual(data["evidence"][0]["value"], "Artist Alpha")

        state = get_session_state(self.user_a.id, "sel_artist_sid")
        self.assertEqual(state["music_entities"].get("last_artist"), "Artist Alpha")

    def test_artist_subtools_explicit_range_coreference_and_isolation(self):
        """Kiem thu 4 sub-tool nghe si voi (artist_name, start_date, end_date), coreference va co lap User A/B."""
        today = timezone.localdate()
        start_str = (today - timedelta(days=2)).isoformat()
        end_str = today.isoformat()

        # 1. Test truc tiep cac sub-tool voi input tuong minh
        ov = tool_artist_listening_overview(self.user_a, "Artist Alpha", start_str, end_str)
        self.assertTrue(ov["found_artist"])
        self.assertEqual(ov["total_plays"], 4)
        self.assertEqual(ov["top_track_name"], "User A Secret Anthem")
        self.assertEqual(ov["top_track_plays"], 4)
        self.assertEqual(ov["share_percentage"], 100.0)

        top_t = tool_artist_top_tracks(self.user_a, "Artist Alpha", start_str, end_str)
        self.assertEqual(top_t["top_track_name"], "User A Secret Anthem")
        self.assertEqual(len(top_t["tracks"]), 1)

        habits = tool_artist_listening_habits(self.user_a, "Artist Alpha", start_str, end_str)
        self.assertGreaterEqual(habits["active_days_count"], 1)
        self.assertIsNotNone(habits["peak_hour_window"])

        comp = tool_artist_period_comparison(self.user_a, "Artist Alpha", start_str, end_str)
        self.assertEqual(comp["current_plays"], 4)

        # Kiem thu trich xuat ngay tu prompt tieng Viet
        parsed_range = extract_date_range_from_text("từ 01/10/2026 đến 15/10/2026")
        self.assertIsNotNone(parsed_range)
        self.assertEqual(parsed_range[0].isoformat(), "2026-10-01")
        self.assertEqual(parsed_range[1].isoformat(), "2026-10-15")

        # 2. Test hoi dap noi tiep qua API: luot 1 tim nghe si -> luot 2 dung dai tu "nghe si do" + khoang ngay
        self.client.force_authenticate(user=self.user_a)
        no_llm_env = {
            "GROQ_API_KEY": "",
            "GEMINI_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
            "OPENAI_BASE_URL": "",
            "OPENAI_API_KEY": "",
        }
        with self.settings(
            GROQ_API_KEY="",
            GEMINI_API_KEY="",
            LLM_BASE_URL="",
            LLM_API_KEY="",
            LLM_MODEL="",
        ):
            with patch.dict("os.environ", no_llm_env, clear=False):
                self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "nghệ sĩ nào tui nghe nhiều nhất năm nay",
                        "mode": "auto",
                        "session_id": "coref_sid",
                    },
                    format="json",
                )

                res_followup = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": f"bài nào của nghệ sĩ đó tui nghe nhiều nhất từ {start_str} đến {end_str}",
                        "mode": "auto",
                        "session_id": "coref_sid",
                    },
                    format="json",
                )

                # User A hoi ve Artist Beta (chi co o User B) -> khong duoc lo du lieu User B
                res_isolated = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": f"Tổng hợp nghệ sĩ Artist Beta từ {start_str} đến {end_str}",
                        "mode": "music_insights",
                        "session_id": "coref_sid",
                    },
                    format="json",
                )

        self.assertEqual(res_followup.status_code, status.HTTP_200_OK)
        f_data = res_followup.json()
        self.assertEqual(f_data["resolved_domain"], "music_insights")
        self.assertEqual(f_data["scope"]["start_date"], start_str)
        self.assertEqual(f_data["scope"]["end_date"], end_str)
        self.assertIn("artist_listening_overview", f_data["meta"]["tools_used"])
        self.assertIn("artist_top_tracks", f_data["meta"]["tools_used"])
        self.assertNotIn("genre_distribution", f_data["meta"]["tools_used"])
        self.assertIn("User A Secret Anthem", f_data["answer"])
        self.assertIn("Artist Alpha", f_data["answer"])
        self.assertTrue(any("Artist Alpha" in ev["label"] for ev in f_data["evidence"]))

        self.assertEqual(res_isolated.status_code, status.HTTP_200_OK)
        iso_data = res_isolated.json()
        self.assertNotIn("User B Private Track", iso_data["answer"])
        self.assertIn("chưa ghi nhận", iso_data["answer"].lower())

    def test_rolling_compressed_memory_beyond_six_turns_and_xml_sanitization(self):
        """Kiem thu nen bo nho sau > 6 luot hoi thoai, truyen vao LLM va loc the noi bo <music_data>."""
        self.client.force_authenticate(user=self.user_a)
        captured_prompts: list[str] = []

        def fake_openai(self_svc, messages):
            captured_prompts.append(messages[-1]["content"])
            return (
                _sanitize_music_answer(
                    "Artist Alpha dẫn đầu với 4 lượt phát trong <music_data>."
                ),
                "openai_compatible",
                "mock-model",
            )

        with patch.object(HybridAssistantService, "_try_openai_compatible_music", fake_openai):
            with patch(
                "ai_engine.services.assistant.service.get_ai_provider_order",
                return_value=["openai_compatible"],
            ):
                last_res = None
                for i in range(1, 9):
                    last_res = self.client.post(
                        "/api/ai/assistant/query/",
                        {
                            "query": f"Lượt {i}: Nghệ sĩ nào tôi nghe nhiều nhất năm nay?",
                            "mode": "music_insights",
                            "session_id": "mem_long_sid",
                        },
                        format="json",
                    )

        self.assertIsNotNone(last_res)
        self.assertEqual(last_res.status_code, status.HTTP_200_OK)
        payload = last_res.json()
        self.assertEqual(payload["meta"]["session_turns"], 8)
        self.assertTrue(payload["meta"]["has_compressed_memory"])
        self.assertNotIn("<music_data>", payload["answer"])

        ctx = get_domain_context(self.user_a.id, "mem_long_sid", "music_insights")
        self.assertEqual(len(ctx["turns"]), 6)
        self.assertTrue(ctx["has_compressed_memory"])
        self.assertIn("Lượt 1", ctx["compressed_memory"])
        self.assertIn("Lượt 2", ctx["compressed_memory"])

        # Luot thu 8 phai nhan duoc ca <session_memory> lan <active_entities>
        self.assertIn("<session_memory>", captured_prompts[-1])
        self.assertIn("Lượt 1", captured_prompts[-1])
        self.assertIn("<active_entities>", captured_prompts[-1])

        # User B voi cung session_id phai bi co lap hoan toan
        ctx_b = get_domain_context(self.user_b.id, "mem_long_sid", "music_insights")
        self.assertEqual(ctx_b["turns"], [])
        self.assertEqual(ctx_b["compressed_memory"], "")

    def test_genre_subtools_matching_evidence_and_sticky_session_period(self):
        """
        Kiem thu:
        1) Hoi DJ (EDM) tra dung top nghe si EDM va Evidence la EDM / Electronic (khong hien V-Pop).
        2) Hoi tiep "tui muon lay ve Alan Walker" van giu pham vi Nam nay tu Persistent Memory
           dù Dashboard dang o Tuan nay.
        3) Khi nguoi dung doi ky tren Dashboard -> chuyen sang ky Dashboard moi.
        """
        now = timezone.now()
        today = timezone.localdate()

        # Tao them nhieu luot V-Pop (de V-Pop dung #1 toan cuc) va 1 nghe si EDM (Alan Walker)
        vpop_artist = Artist.objects.create(spotify_id="art_sivan_test", name="Sơn Tùng M-TP")
        vpop_album = Album.objects.create(spotify_id="alb_vpop_test", name="Chúng Ta", image_url="")
        vpop_album.artists.add(vpop_artist)
        vpop_track = Track.objects.create(
            spotify_id="trk_vpop_test",
            name="Chúng Ta Của Hiện Tại",
            duration_ms=240000,
            album=vpop_album,
            danceability=0.65,
            energy=0.60,
            valence=0.55,
            acousticness=0.30,
            tempo=110.0,
            features_synced=True,
            features_source="spotify",
        )
        vpop_track.artists.add(vpop_artist)

        edm_artist = Artist.objects.create(spotify_id="art_aw_test", name="Alan Walker")
        edm_album = Album.objects.create(spotify_id="alb_aw_test", name="Different World", image_url="")
        edm_album.artists.add(edm_artist)
        edm_track = Track.objects.create(
            spotify_id="trk_aw_test",
            name="Faded",
            duration_ms=212000,
            album=edm_album,
            danceability=0.68,
            energy=0.86,
            valence=0.45,
            acousticness=0.10,
            tempo=128.0,
            features_synced=True,
            features_source="spotify",
        )
        edm_track.artists.add(edm_artist)

        # 6 luot V-Pop trong thang nay (khong phai tuan nay) & 3 luot Alan Walker (2 luot cach day 15 ngay, 1 luot hom nay)
        for i in range(6):
            ListeningHistory.objects.create(
                user=self.user_a,
                track=vpop_track,
                played_at=now - timedelta(days=20, hours=i),
            )
        ListeningHistory.objects.create(
            user=self.user_a,
            track=edm_track,
            played_at=now - timedelta(days=15, hours=1),
        )
        ListeningHistory.objects.create(
            user=self.user_a,
            track=edm_track,
            played_at=now - timedelta(days=15, hours=2),
        )
        ListeningHistory.objects.create(
            user=self.user_a,
            track=edm_track,
            played_at=now - timedelta(minutes=25),
        )

        # Kiem tra truc tiep 3 sub-tool the loai
        year_start = f"{today.year}-01-01"
        year_end = f"{today.year}-12-31"
        g_ov = tool_genre_listening_overview(self.user_a, "EDM / Electronic", year_start, year_end)
        self.assertGreaterEqual(g_ov["total_plays"], 3)
        g_art = tool_genre_top_artists(self.user_a, "EDM / Electronic", year_start, year_end)
        self.assertTrue(any(a["name"] == "Alan Walker" for a in g_art["artists"]))
        g_trk = tool_genre_top_tracks(self.user_a, "EDM / Electronic", year_start, year_end)
        self.assertTrue(any(t["name"] == "Faded" for t in g_trk["tracks"]))

        # Kiem tra luong 3 luot qua API
        self.client.force_authenticate(user=self.user_a)
        week_mon = (today - timedelta(days=today.weekday())).isoformat()
        week_sun = (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat()
        dash_week_ctx = {
            "period_type": "week",
            "start_date": week_mon,
            "end_date": week_sun,
            "label": "Tuần này",
        }
        no_llm_env = {
            "GROQ_API_KEY": "",
            "GEMINI_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
            "OPENAI_BASE_URL": "",
            "OPENAI_API_KEY": "",
        }
        with self.settings(
            GROQ_API_KEY="",
            GEMINI_API_KEY="",
            LLM_BASE_URL="",
            LLM_API_KEY="",
            LLM_MODEL="",
        ):
            with patch.dict("os.environ", no_llm_env, clear=False):
                # Luot 1: Hoi DJ (EDM) nam nay (Dashboard dang o Tuan nay)
                res_1 = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "vậy DJ (EDM) nào tui nghe nhiều nhất trong năm nay",
                        "mode": "auto",
                        "session_id": "genre_sticky_sid",
                        "period_context": dash_week_ctx,
                    },
                    format="json",
                )
                # Luot 2: Noi tiep "tui muon lay ve Alan Walker" (Dashboard VAN o Tuan nay -> giu Nam nay!)
                res_2 = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "tui muốn lấy về Alan Walker",
                        "mode": "auto",
                        "session_id": "genre_sticky_sid",
                        "period_context": dash_week_ctx,
                    },
                    format="json",
                )
                # Luot 3: Nguoi dung doi ky Dashboard sang Thang 01/2020 -> phai cap nhat sang Thang 01/2020
                res_3 = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "tui muốn lấy về Alan Walker",
                        "mode": "auto",
                        "session_id": "genre_sticky_sid",
                        "period_context": {
                            "period_type": "month",
                            "start_date": "2020-01-01",
                            "end_date": "2020-01-31",
                            "label": "Tháng 01/2020",
                        },
                    },
                    format="json",
                )

        self.assertEqual(res_1.status_code, status.HTTP_200_OK)
        d1 = res_1.json()
        self.assertEqual(d1["resolved_domain"], "music_insights")
        self.assertEqual(d1["scope"]["label"], f"Năm {today.year}")
        self.assertIn("genre_listening_overview", d1["meta"]["tools_used"])
        self.assertIn("genre_top_artists", d1["meta"]["tools_used"])
        ev1_labels = [e["label"] for e in d1["evidence"]]
        self.assertTrue(any("EDM / Electronic" in lbl for lbl in ev1_labels))
        self.assertFalse(any("V-Pop" in str(e["value"]) for e in d1["evidence"]))

        self.assertEqual(res_2.status_code, status.HTTP_200_OK)
        d2 = res_2.json()
        self.assertEqual(d2["resolved_domain"], "music_insights")
        # Phai giu nguyen pham vi Nam nay (3 luot Alan Walker), khong roi ve Tuan nay (1 luot)!
        self.assertEqual(d2["scope"]["label"], f"Năm {today.year}")
        self.assertIn("bộ nhớ phiên", d2["scope"]["note"].lower())
        self.assertIn("Alan Walker", d2["answer"])
        self.assertIn("3 lượt phát", d2["answer"])

        self.assertEqual(res_3.status_code, status.HTTP_200_OK)
        d3 = res_3.json()
        self.assertEqual(d3["scope"]["label"], "Tháng 01/2020")
        self.assertIn("0 lượt phát", d3["answer"])

    def test_agentic_memory_crud_tool_and_inline_memory_ops(self):
        """Kiem thu tool_update_session_memory (add/set/update/delete) va Agent tu cap nhat qua <memory_ops>."""
        # 1. Test truc tiep CRUD tool
        res_add = tool_update_session_memory(
            self.user_a.id,
            "crud_sid",
            "music_insights",
            [
                {"action": "set", "field": "active_artist", "value": "SIVAN"},
                {"action": "set", "field": "user_preferences", "key": "format", "value": "bảng ngắn gọn"},
                {"action": "add", "field": "pinned_facts", "key": "fact_1", "value": "SIVAN: 663 lượt năm 2026"},
                {"action": "set", "field": "unknown_field", "value": "hack"},  # phai bi bo qua
            ],
        )
        self.assertEqual(res_add["applied"], 3)
        self.assertEqual(res_add["skipped"], 1)
        self.assertEqual(res_add["persistent_memory"]["active_artist"], "SIVAN")
        self.assertEqual(res_add["persistent_memory"]["user_preferences"]["format"], "bảng ngắn gọn")

        # Update & delete
        res_mod = tool_update_session_memory(
            self.user_a.id,
            "crud_sid",
            "music_insights",
            [
                {"action": "update", "field": "user_preferences", "key": "format", "value": "danh sách bullet"},
                {"action": "delete", "field": "active_artist"},
                {"action": "delete", "field": "pinned_facts", "key": "fact_1"},
            ],
        )
        self.assertEqual(res_mod["applied"], 3)
        self.assertIsNone(res_mod["persistent_memory"]["active_artist"])
        self.assertEqual(res_mod["persistent_memory"]["user_preferences"]["format"], "danh sách bullet")
        self.assertEqual(res_mod["persistent_memory"]["pinned_facts"], {})

        # Test tach & an <memory_ops>
        raw_out = (
            'Mình đã ghi nhớ bạn thích xem dạng bảng.\n'
            '<memory_ops>[{"action":"set","field":"user_preferences","key":"style","value":"bảng Markdown"}]</memory_ops>'
        )
        clean_out, ops = extract_and_strip_memory_ops(raw_out)
        self.assertEqual(clean_out, "Mình đã ghi nhớ bạn thích xem dạng bảng.")
        self.assertEqual(len(ops), 1)

        # 2. Test end-to-end Agent phat lenh <memory_ops> trong 1 luot tra loi va luot sau doc duoc
        self.client.force_authenticate(user=self.user_a)
        captured_payloads: list[str] = []

        def fake_llm_with_mem_ops(self_svc, messages):
            captured_payloads.append(messages[-1]["content"])
            if len(captured_payloads) == 1:
                return (
                    "Artist Alpha là nghệ sĩ dẫn đầu của bạn.\n"
                    '<memory_ops>[{"action":"set","field":"user_preferences","key":"display_format","value":"bảng Markdown"}]</memory_ops>',
                    "openai_compatible",
                    "mock-model",
                )
            return ("Đây là bảng thống kê theo sở thích bạn đã lưu.", "openai_compatible", "mock-model")

        with patch.object(HybridAssistantService, "_try_openai_compatible_music", fake_llm_with_mem_ops):
            with patch(
                "ai_engine.services.assistant.service.get_ai_provider_order",
                return_value=["openai_compatible"],
            ):
                r1 = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Nghệ sĩ nào tôi nghe nhiều nhất năm nay? Nhớ giúp tui thích xem dạng bảng.",
                        "mode": "music_insights",
                        "session_id": "agent_mem_sid",
                    },
                    format="json",
                )
                r2 = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Top bài hát của tôi thì sao?",
                        "mode": "music_insights",
                        "session_id": "agent_mem_sid",
                    },
                    format="json",
                )

        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        d1 = r1.json()
        self.assertNotIn("<memory_ops>", d1["answer"])
        self.assertIn("session_memory_update", d1["meta"]["tools_used"])

        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertIn("<session_persistent_memory>", captured_payloads[1])
        self.assertIn("display_format: bảng Markdown", captured_payloads[1])

    def test_vpop_artist_list_query_routes_to_genre_tools_not_unknown_artist(self):
        """
        Kiem thu cau hoi 'Liet ke 5 nghe si VPOP tui nghe nhieu nhat':
        - Khong doan nham 'VPOP tui nghe' thanh ten nghe si khong ton tai.
        - Dinh tuyen dung sang genre_summary (V-Pop) -> genre_listening_overview + genre_top_artists.
        - Hien thi dung danh sach nghe si V-Pop thuc te va Evidence cua V-Pop.
        """
        now = timezone.now()
        today = timezone.localdate()

        vpop_1 = Artist.objects.create(spotify_id="art_sontung_vpop", name="Sơn Tùng M-TP")
        alb_1 = Album.objects.create(spotify_id="alb_st_vpop", name="m-tp M-TP", image_url="")
        alb_1.artists.add(vpop_1)
        trk_1 = Track.objects.create(
            spotify_id="trk_st_vpop",
            name="Nơi Này Có Anh",
            duration_ms=260000,
            album=alb_1,
            danceability=0.68,
            energy=0.65,
            valence=0.72,
            acousticness=0.25,
            tempo=112.0,
            features_synced=True,
            features_source="spotify",
        )
        trk_1.artists.add(vpop_1)

        vpop_2 = Artist.objects.create(spotify_id="art_denvau_vpop", name="Đen Vâu")
        alb_2 = Album.objects.create(spotify_id="alb_dv_vpop", name="Show Của Đen", image_url="")
        alb_2.artists.add(vpop_2)
        trk_2 = Track.objects.create(
            spotify_id="trk_dv_vpop",
            name="Nấu Ăn Cho Em",
            duration_ms=245000,
            album=alb_2,
            danceability=0.64,
            energy=0.58,
            valence=0.62,
            acousticness=0.40,
            tempo=96.0,
            features_synced=True,
            features_source="spotify",
        )
        trk_2.artists.add(vpop_2)

        for idx in range(3):
            ListeningHistory.objects.create(
                user=self.user_a,
                track=trk_1,
                played_at=now - timedelta(minutes=10 + idx * 5),
            )
        ListeningHistory.objects.create(
            user=self.user_a,
            track=trk_2,
            played_at=now - timedelta(minutes=30),
        )

        self.client.force_authenticate(user=self.user_a)
        week_mon = (today - timedelta(days=today.weekday())).isoformat()
        week_sun = (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat()
        no_llm_env = {
            "GROQ_API_KEY": "",
            "GEMINI_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
            "OPENAI_BASE_URL": "",
            "OPENAI_API_KEY": "",
        }
        with self.settings(
            GROQ_API_KEY="",
            GEMINI_API_KEY="",
            LLM_BASE_URL="",
            LLM_API_KEY="",
            LLM_MODEL="",
        ):
            with patch.dict("os.environ", no_llm_env, clear=False):
                res = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Liệt kê 5 nghệ sĩ VPOP tui nghe nhiều nhất",
                        "mode": "auto",
                        "session_id": "vpop_genre_sid",
                        "period_context": {
                            "period_type": "week",
                            "start_date": week_mon,
                            "end_date": week_sun,
                            "label": "Tuần này",
                        },
                    },
                    format="json",
                )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["resolved_domain"], "music_insights")
        self.assertIn("genre_listening_overview", data["meta"]["tools_used"])
        self.assertIn("genre_top_artists", data["meta"]["tools_used"])
        self.assertNotIn("artist_listening_overview", data["meta"]["tools_used"])
        self.assertNotIn("VPOP tui nghe", data["answer"])
        self.assertIn("Sơn Tùng M-TP", data["answer"])
        ev_labels = [ev["label"] for ev in data["evidence"]]
        self.assertIn("Thể loại: V-Pop", ev_labels)
        self.assertIn("Nghệ sĩ nổi bật (V-Pop)", ev_labels)

    def test_zero_data_and_missing_artist_use_llm_instead_of_hardcoded_guard(self):
        """
        Khi ky co 0 luot phat hoac khong tim thay nghe si, van goi LLM de tra loi tu nhien
        kem zero_data_context va all_time_user_plays (khong ep qua zero_data_guard).
        """
        self.client.force_authenticate(user=self.user_a)
        captured_payloads: list[str] = []

        def fake_llm_zero_data(self_svc, messages):
            captured_payloads.append(messages[-1]["content"])
            return (
                "Trong kỳ này chưa có lượt phát phù hợp, bạn thử chọn phạm vi rộng hơn bên dưới nhé.",
                "openai_compatible",
                "mock-model",
            )

        with patch.object(HybridAssistantService, "_try_openai_compatible_music", fake_llm_zero_data):
            with patch(
                "ai_engine.services.assistant.service.get_ai_provider_order",
                return_value=["openai_compatible"],
            ):
                res_empty = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Tổng kết gu nghe nhạc của tôi",
                        "mode": "music_insights",
                        "session_id": "zero_llm_sid_1",
                        "period_context": {
                            "period_type": "month",
                            "start_date": "2020-01-01",
                            "end_date": "2020-01-31",
                            "label": "Tháng 01/2020",
                        },
                    },
                    format="json",
                )
                res_missing_artist = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Tổng hợp nghệ sĩ Nghệ Sĩ Không Tồn Tại trong tuần này",
                        "mode": "music_insights",
                        "session_id": "zero_llm_sid_2",
                    },
                    format="json",
                )

        self.assertEqual(res_empty.status_code, status.HTTP_200_OK)
        d_empty = res_empty.json()
        self.assertEqual(d_empty["meta"]["model_name"], "mock-model")
        self.assertNotEqual(d_empty["meta"]["model_name"], "zero_data_guard")
        self.assertFalse(d_empty["meta"]["is_fallback"])
        self.assertIn("chưa có lượt phát phù hợp", d_empty["answer"])

        self.assertEqual(res_missing_artist.status_code, status.HTTP_200_OK)
        d_missing = res_missing_artist.json()
        self.assertEqual(d_missing["meta"]["model_name"], "mock-model")
        self.assertNotEqual(d_missing["meta"]["model_name"], "zero_data_guard")
        self.assertEqual(len(captured_payloads), 2)
        for payload in captured_payloads:
            self.assertIn("zero_data_context", payload)
            self.assertIn("all_time_user_plays", payload)

    def test_hybrid_suggested_scopes_included_when_period_omitted_and_omitted_when_explicit(self):
        """
        - Khi cau hoi khong neu moc thoi gian (dung ky Dashboard), tra ve suggested_scopes (>=2) khong trung ky dang chon.
        - Khi cau hoi neu ro moc thoi gian va co du lieu, suggested_scopes la [].
        """
        self.client.force_authenticate(user=self.user_a)
        today = timezone.localdate()
        week_mon = (today - timedelta(days=today.weekday())).isoformat()
        week_sun = (today - timedelta(days=today.weekday()) + timedelta(days=6)).isoformat()

        no_llm_env = {
            "GROQ_API_KEY": "",
            "GEMINI_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
            "OPENAI_BASE_URL": "",
            "OPENAI_API_KEY": "",
        }
        with self.settings(
            GROQ_API_KEY="",
            GEMINI_API_KEY="",
            LLM_BASE_URL="",
            LLM_API_KEY="",
            LLM_MODEL="",
        ):
            with patch.dict("os.environ", no_llm_env, clear=False):
                res_omitted = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Top nghệ sĩ của tôi",
                        "mode": "music_insights",
                        "session_id": "quick_scope_sid_1",
                        "period_context": {
                            "period_type": "week",
                            "start_date": week_mon,
                            "end_date": week_sun,
                            "label": "Tuần này",
                        },
                    },
                    format="json",
                )
                res_explicit = self.client.post(
                    "/api/ai/assistant/query/",
                    {
                        "query": "Top nghệ sĩ của tôi trong năm nay",
                        "mode": "music_insights",
                        "session_id": "quick_scope_sid_2",
                        "period_context": {
                            "period_type": "week",
                            "start_date": week_mon,
                            "end_date": week_sun,
                            "label": "Tuần này",
                        },
                    },
                    format="json",
                )

        self.assertEqual(res_omitted.status_code, status.HTTP_200_OK)
        d_omit = res_omitted.json()
        scopes = d_omit.get("suggested_scopes") or []
        self.assertGreaterEqual(len(scopes), 2)
        self.assertFalse(any(s["label"] == "Xem Tuần này" for s in scopes))

        self.assertEqual(res_explicit.status_code, status.HTTP_200_OK)
        d_exp = res_explicit.json()
        self.assertEqual(d_exp.get("suggested_scopes"), [])
