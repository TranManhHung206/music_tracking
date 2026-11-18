"""
HybridAssistantService - Bo dieu phoi trung tam cho MusicTrack Assistant.
Ket hop Music Insights (User-Scoped Analytics Tools) va Website Support (Codebase RAG).
"""

import json
import logging
import os
import re
from django.conf import settings

from .schemas import (
    AssistantClarificationOption,
    AssistantEvidenceItem,
    AssistantModeLiteral,
    AssistantQueryResult,
    AssistantResponseMeta,
    AssistantScopeMeta,
    AssistantTopicItem,
)
from .intent_router import OUT_OF_SCOPE_TRIVIA_CUES, normalize_vi_text, route_assistant_intent
from .session_store import append_domain_turn, get_domain_turns, get_session_state
from .music_tools import collect_music_insights_bundle
from .website_support import query_website_support

logger = logging.getLogger(__name__)

_EMOJI_REGEX = re.compile(
    "["
    "\U0001F300-\U0001F6FF"
    "\U0001F900-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E0-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)

MUSIC_GROUNDING_SYSTEM_PROMPT = """Bạn là MusicTrack Assistant - trợ lý đồng hành phân tích âm nhạc cá nhân của chính người dùng đang đăng nhập.
Nhiệm vụ: Trả lời ngắn gọn, rõ ràng, tự nhiên bằng tiếng Việt có dấu dựa DUY NHẤT trên dữ liệu tổng hợp được cung cấp trong JSON <music_data>.

CÁC QUY TẮC BẮT BUỘC:
1. TRUNG THỰC VỚI SỐ LIỆU: Chỉ nêu con số, tên bài hát, nghệ sĩ, album, thể loại và tỷ lệ thực sự có trong <music_data>. Tuyệt đối không bịa đặt dữ liệu.
2. PHÂN BIỆT RÕ BẢN CHẤT SỐ LIỆU:
   - Nêu rõ phạm vi kỳ dữ liệu đang dùng (ví dụ: Tuần này, Tháng 11/2026...).
   - Khi nhắc đến thời lượng nghe, nói rõ là ước tính theo độ dài chuẩn các bài hát đã phát.
   - Khi nhắc đến Audio Features hoặc thể loại nhạc, nếu provenance có ước lượng hoặc phân loại tự động của MusicTrack thì ghi chú ngắn gọn, không khẳng định 100% là số liệu đo trực tiếp từ Spotify.
   - Với AI Music Persona hoặc lời khuyên, nêu rõ đó là phần tổng hợp diễn giải của AI.
3. KHÔNG SUY DIỄN TÂM LÝ VÔ CĂN CỨ: Không tự kết luận lý do nhân quả tại sao người dùng nghe một bài hát hay nghe vào một khung giờ (chỉ mô tả mẫu hành vi quan sát được).
4. XƯNG HÔ THÂN THIỆN: Xưng hô là "mình" và "bạn".
5. TUYỆT ĐỐI KHÔNG DÙNG EMOJI hoặc icon ký tự ở bất kỳ đâu."""


def _strip_emojis(text: str) -> str:
    return _EMOJI_REGEX.sub("", text or "").strip()


def _build_music_fallback_answer(aggregates: dict, scope_label: str) -> str:
    """Tao cau tra loi tieng Viet xac dinh tu so lieu that khi LLM offline hoac timeout."""
    summary = aggregates.get("summary") or {}
    total_plays = int(summary.get("total_plays") or 0)
    unique_tracks = int(summary.get("unique_tracks_count") or 0)
    unique_artists = int(summary.get("unique_artists_count") or 0)
    unique_albums = int(summary.get("unique_albums_count") or 0)
    duration_label = summary.get("estimated_duration_label") or "0 phút"

    if total_plays == 0:
        return (
            f"Trong phạm vi {scope_label}, hệ thống chưa ghi nhận lượt phát nào của bạn (0 lượt phát). "
            "Bạn hãy thử chọn một kỳ thời gian khác trên bảng phân tích hoặc bấm Đồng bộ để cập nhật lịch sử nghe mới nhất."
        )

    lines = [
        f"Trong phạm vi **{scope_label}**, dữ liệu thực tế ghi nhận bạn có **{total_plays:,} lượt phát** "
        f"trên {unique_tracks:,} bài hát khác nhau, {unique_artists:,} nghệ sĩ và {unique_albums:,} album. "
        f"Thời lượng nghe ước tính (cộng dồn độ dài chuẩn các bản nhạc đã phát) đạt khoảng **{duration_label}**."
    ]

    prev_plays = int(summary.get("previous_period_plays") or 0)
    growth = summary.get("growth_percentage")
    baseline_status = summary.get("baseline_status")
    prev_label = summary.get("previous_period_label") or "kỳ trước"
    if baseline_status == "new_activity":
        lines.append(f"- So với {prev_label} (0 lượt): Đây là hoạt động nghe nhạc mới của bạn trong kỳ này.")
    elif growth is not None:
        sign = "+" if growth > 0 else ""
        lines.append(f"- So với {prev_label} ({prev_plays:,} lượt): Mức thay đổi là **{sign}{growth}%**.")

    top_tracks = aggregates.get("top_tracks") or []
    if top_tracks:
        track_str = ", ".join(
            f"{t['name']} ({t['play_count']} lượt)" for t in top_tracks[:3]
        )
        lines.append(f"- Top bài hát nghe nhiều nhất: {track_str}.")

    top_artists = aggregates.get("top_artists") or []
    if top_artists:
        artist_str = ", ".join(
            f"{a['name']} ({a['play_count']} lượt)" for a in top_artists[:3]
        )
        lines.append(f"- Top nghệ sĩ nổi bật: {artist_str}.")

    genres_block = aggregates.get("genres") or {}
    genres_list = genres_block.get("distribution") or []
    if genres_list:
        genre_str = ", ".join(f"{g['name']} ({g['percentage']}%)" for g in genres_list[:3])
        lines.append(f"- Phân bố thể loại (theo bộ phân loại kết hợp của MusicTrack): {genre_str}.")

    audio_block = aggregates.get("audio_features") or {}
    highest = audio_block.get("highest_trait")
    prov = audio_block.get("provenance") or {}
    if highest:
        measured_pct = prov.get("measured_percentage", 0.0)
        lines.append(
            f"- Đặc trưng âm thanh nổi bật nhất là {highest['attribute']} ({round(highest['score'] * 100)}%). "
            f"Nguồn gốc chỉ số: {measured_pct}% lượt phát được đo từ dữ liệu âm thanh, phần còn lại có thể là ước lượng hoặc chưa đủ thông số."
        )

    patterns = aggregates.get("listening_patterns") or {}
    peak_windows = patterns.get("peak_windows") or []
    if peak_windows:
        lines.append(f"- Khung giờ nghe nổi bật trong kỳ: {', '.join(peak_windows[:2])}.")

    knn_block = aggregates.get("knn_recommendations") or {}
    if knn_block.get("has_seed") and knn_block.get("recommendations"):
        seed = knn_block["seed_track"]
        recs = ", ".join(
            f"{r['name']} - {', '.join(r.get('artists') or ['Nghệ sĩ'])} (tương đồng {round(r['similarity_score'] * 100)}%)"
            for r in knn_block["recommendations"][:3]
        )
        lines.append(f"- Gợi ý KNN tương đồng với bài **{seed['name']}**: {recs}.")

    persona = aggregates.get("latest_persona")
    if persona:
        lines.append(
            f"- Hồ sơ AI Music Persona gần nhất (tổng hợp diễn giải cửa sổ 30 ngày): "
            f"**{persona['persona_title']}** - {persona['tagline']}"
        )
    elif aggregates.get("persona_status") == "missing":
        lines.append(
            "- Hồ sơ AI Music Persona: Bạn chưa tạo hồ sơ nào. Hãy bấm nút 'Phân tích AI Persona' trên Dashboard để tạo bản phân tích cá tính âm nhạc của riêng bạn."
        )

    return "\n\n".join(lines)


class HybridAssistantService:
    """Service dieu phoi MusicTrack Assistant cho ca Music Insights va Website Support."""

    def _synthesize_music_with_llm(
        self,
        query_text: str,
        aggregates: dict,
        recent_turns: list[dict],
    ) -> tuple[str | None, str, str]:
        """Goi Groq (120b -> 20b -> 8b) hoac Gemini voi chi so lieu tong hop."""
        compact_turns = [
            {"user": t.get("query", ""), "assistant_summary": t.get("answer_summary", "")}
            for t in recent_turns[-4:]
        ]
        user_payload = (
            "<conversation_history>\n"
            + json.dumps(compact_turns, ensure_ascii=False)
            + "\n</conversation_history>\n\n"
            + "<music_data>\n"
            + json.dumps(aggregates, ensure_ascii=False)
            + "\n</music_data>\n\n"
            + f"Câu hỏi hiện tại của bạn: {query_text}\n"
            + "Hãy trả lời đúng sự thật dựa trên <music_data>, nêu rõ kỳ dữ liệu và phân biệt rõ ước tính/thực tế."
        )
        messages = [
            {"role": "system", "content": MUSIC_GROUNDING_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ]

        groq_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                from groq import Groq
                client = Groq(api_key=groq_key)
                models = [
                    getattr(settings, "AI_MODEL_GROQ", "openai/gpt-oss-120b"),
                    getattr(settings, "AI_MODEL_GROQ_BACKUP", "openai/gpt-oss-20b"),
                    "llama-3.1-8b-instant",
                ]
                for model_name in models:
                    try:
                        res = client.chat.completions.create(
                            model=model_name,
                            messages=messages,
                            temperature=0.25,
                            max_tokens=700,
                        )
                        txt = _strip_emojis(res.choices[0].message.content or "")
                        if txt:
                            return txt, "groq", model_name
                    except Exception as exc:
                        logger.warning("Assistant Groq %s that bai: %s", model_name, exc)
            except Exception as exc:
                logger.warning("Khong the khoi tao Groq client: %s", exc)

        gemini_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                prompt_text = f"{MUSIC_GROUNDING_SYSTEM_PROMPT}\n\n{user_payload}"
                for gem_model in ("gemini-2.5-flash", "gemini-1.5-flash"):
                    try:
                        res = client.models.generate_content(model=gem_model, contents=prompt_text)
                        txt = _strip_emojis(getattr(res, "text", "") or "")
                        if txt:
                            return txt, "gemini", gem_model
                    except Exception as exc:
                        logger.warning("Assistant Gemini %s that bai: %s", gem_model, exc)
            except Exception as exc:
                logger.warning("Khong the khoi tao Gemini client: %s", exc)

        return None, "local_music_synthesizer", "deterministic_music_v1"

    def handle_query(
        self,
        user,
        query_text: str,
        mode: AssistantModeLiteral = "auto",
        session_id: str | None = "default",
        period_context: dict | None = None,
        rag_mode: str = "full_cascade",
        top_k: int = 5,
        use_cache: bool = True,
    ) -> AssistantQueryResult:
        """Xu ly mot luot hoi dap hoan chinh voi co lap User Scope va Session Context."""
        if not user or not getattr(user, "is_authenticated", False):
            raise ValueError("Yêu cầu đăng nhập hợp lệ.")

        is_staff = bool(getattr(user, "is_staff", False))
        session_state = get_session_state(user.id, session_id)
        decision = route_assistant_intent(
            query=query_text,
            requested_mode=mode,
            last_domain=session_state.get("last_domain"),
        )

        # 1. Truong hop y dinh mo ho o che do Auto -> Hoi lam ro, khong goi mu ca 2 mien
        if decision.needs_clarification:
            clarification_options = [
                AssistantClarificationOption(
                    mode="music_insights",
                    label="Xem Dữ liệu Âm nhạc cá nhân",
                    query=f"Phân tích tổng quan và thói quen nghe nhạc của tôi ({query_text})",
                ),
                AssistantClarificationOption(
                    mode="website_support",
                    label="Hỏi về Cách hoạt động Website",
                    query=f"Giải thích cách hoạt động của hệ thống MusicTrack liên quan đến: {query_text}",
                ),
            ]
            answer = (
                "Mình chưa rõ bạn đang muốn hỏi về **số liệu nghe nhạc cá nhân** của bạn "
                "hay hỏi về **cách hoạt động và tính năng của website MusicTrack**. "
                "Bạn chọn một hướng bên dưới hoặc chuyển chế độ tương ứng để mình hỗ trợ chính xác nhé."
            )
            return AssistantQueryResult(
                query=query_text,
                answer=answer,
                active_mode=mode,
                resolved_domain="clarification",
                needs_clarification=True,
                clarification_options=clarification_options,
                scope=AssistantScopeMeta(
                    label="Cần làm rõ ý định",
                    source="clarification",
                    note="Chọn một trong hai miền tri thức để có câu trả lời chính xác.",
                ),
                evidence=[],
                topics=[],
                dev_citations=[],
                dev_verification=None,
                dev_metrics=None,
                meta=AssistantResponseMeta(
                    provider_used="intent_router",
                    model_name="clarification_gate",
                    is_fallback=False,
                    tools_used=["intent_router"],
                    session_turns=len(session_state.get("music_turns", [])) + len(session_state.get("website_turns", [])),
                ),
            )

        # 2. Mien Du lieu Am nhac ca nhan (Music Insights)
        if decision.resolved_domain == "music_insights":
            norm_q = normalize_vi_text(query_text)
            if any(trivia in norm_q for trivia in OUT_OF_SCOPE_TRIVIA_CUES):
                return AssistantQueryResult(
                    query=query_text,
                    answer=(
                        "Câu hỏi này nằm ngoài phạm vi dữ liệu âm nhạc cá nhân trên MusicTrack. "
                        "Bạn có thể hỏi về lượt phát, bài hát/nghệ sĩ/album nổi bật, so sánh giữa các kỳ, "
                        "chỉ số Audio Features, khung giờ nghe nhạc hoặc gợi ý bài hát tương đồng."
                    ),
                    active_mode=mode,
                    resolved_domain="music_insights",
                    needs_clarification=False,
                    clarification_options=[],
                    scope=AssistantScopeMeta(
                        label="Ngoài phạm vi dữ liệu âm nhạc",
                        source="rolling_window",
                        note="Không sử dụng dữ liệu nghe nhạc cho câu hỏi không liên quan.",
                    ),
                    evidence=[],
                    topics=[],
                    dev_citations=[],
                    dev_verification=None,
                    dev_metrics=None,
                    meta=AssistantResponseMeta(
                        provider_used="intent_router",
                        model_name="out_of_scope_guard",
                        is_fallback=False,
                        tools_used=["out_of_scope_guard"],
                        session_turns=len(session_state.get("music_turns", [])),
                    ),
                )

            music_turns = get_domain_turns(user.id, session_id, "music_insights")
            bundle = collect_music_insights_bundle(
                user=user,
                query_text=query_text,
                period_context=period_context,
                top_k=top_k,
            )
            aggregates = bundle["aggregates"]
            total_plays = int(aggregates["summary"]["total_plays"])
            scope: AssistantScopeMeta = bundle["scope"]

            if total_plays == 0:
                answer = _build_music_fallback_answer(aggregates, scope.label)
                provider_used = "local_music_synthesizer"
                model_name = "zero_data_guard"
                is_fallback = False
            else:
                llm_answer, provider_used, model_name = self._synthesize_music_with_llm(
                    query_text=query_text,
                    aggregates=aggregates,
                    recent_turns=music_turns,
                )
                if llm_answer:
                    answer = llm_answer
                    is_fallback = False
                else:
                    answer = _build_music_fallback_answer(aggregates, scope.label)
                    is_fallback = True

            turns_count = append_domain_turn(
                user_id=user.id,
                session_id=session_id,
                domain="music_insights",
                user_query=query_text,
                answer_text=answer,
                scope_label=scope.label,
            )
            return AssistantQueryResult(
                query=query_text,
                answer=answer,
                active_mode=mode,
                resolved_domain="music_insights",
                needs_clarification=False,
                clarification_options=[],
                scope=scope,
                evidence=bundle["evidence"],
                topics=[
                    AssistantTopicItem(
                        id="music-scope",
                        title=f"Dữ liệu cá nhân kỳ: {scope.label}",
                        category="Phân tích nghe nhạc",
                    )
                ],
                dev_citations=[],
                dev_verification=None,
                dev_metrics=None,
                meta=AssistantResponseMeta(
                    provider_used=provider_used,
                    model_name=model_name,
                    is_fallback=is_fallback,
                    tools_used=bundle["tools_used"],
                    session_turns=turns_count,
                ),
            )

        # 3. Mien Ho tro Website (Website Support RAG)
        website_turns = get_domain_turns(user.id, session_id, "website_support")
        ws_res = query_website_support(
            query_text=query_text,
            is_staff=is_staff,
            rag_mode_str=rag_mode,
            top_k=top_k,
            use_cache=use_cache,
            website_turns=website_turns,
        )
        turns_count = append_domain_turn(
            user_id=user.id,
            session_id=session_id,
            domain="website_support",
            user_query=query_text,
            answer_text=ws_res["answer"],
            scope_label=ws_res["scope"].label,
        )
        return AssistantQueryResult(
            query=query_text,
            answer=ws_res["answer"],
            active_mode=mode,
            resolved_domain="website_support",
            needs_clarification=False,
            clarification_options=[],
            scope=ws_res["scope"],
            evidence=[],
            topics=ws_res["topics"],
            dev_citations=ws_res["dev_citations"] if is_staff else [],
            dev_verification=ws_res["dev_verification"] if is_staff else None,
            dev_metrics=ws_res["dev_metrics"] if is_staff else None,
            meta=AssistantResponseMeta(
                provider_used=ws_res["provider_used"],
                model_name=ws_res["model_name"],
                is_fallback=ws_res["is_fallback"],
                tools_used=ws_res["tools_used"],
                session_turns=turns_count,
            ),
        )


_assistant_singleton: HybridAssistantService | None = None


def get_assistant_service() -> HybridAssistantService:
    """Tra ve singleton cua HybridAssistantService."""
    global _assistant_singleton
    if _assistant_singleton is None:
        _assistant_singleton = HybridAssistantService()
    return _assistant_singleton
