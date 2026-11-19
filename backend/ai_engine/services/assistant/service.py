"""
HybridAssistantService - Bo dieu phoi trung tam cho MusicTrack Assistant.
Ket hop Music Insights (Selective User-Scoped Tools + Artist/Genre Sub-Tools),
Website Support (Codebase RAG) va kien truc bo nho 2 lop (Session Persistent Memory + Episodic Memory)
co ho tro Agent tu cap nhat memory qua tool_update_session_memory.
"""

import json
import logging
import os
import re
from django.conf import settings

from ai_engine.services.llm_client import (
    OpenAICompatibleClient,
    get_ai_provider_order,
    get_openai_compatible_config,
    strip_reasoning_blocks,
)
from .schemas import (
    AssistantClarificationOption,
    AssistantModeLiteral,
    AssistantQueryResult,
    AssistantResponseMeta,
    AssistantScopeMeta,
    AssistantTopicItem,
)
from .intent_router import OUT_OF_SCOPE_TRIVIA_CUES, normalize_vi_text, route_assistant_intent
from .session_store import append_domain_turn, get_domain_context, get_session_state
from .memory_tools import extract_and_strip_memory_ops, tool_update_session_memory
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

_INTERNAL_TAG_PHRASE_REGEX = re.compile(
    r"(?:trong|từ|theo|của)\s+`?<(?:music_data|conversation_history|session_memory|session_persistent_memory|active_entities|memory_ops)>`?",
    flags=re.IGNORECASE,
)
_INTERNAL_TAG_REGEX = re.compile(
    r"`?</?(?:music_data|conversation_history|session_memory|session_persistent_memory|active_entities|memory_ops)>`?",
    flags=re.IGNORECASE,
)

MUSIC_GROUNDING_SYSTEM_PROMPT = """Bạn là MusicTrack Assistant - trợ lý đồng hành phân tích âm nhạc cá nhân của chính người dùng đang đăng nhập.
Nhiệm vụ: Trả lời ngắn gọn, đúng trọng tâm, rõ ràng và tự nhiên bằng tiếng Việt có dấu dựa DUY NHẤT trên số liệu được cung cấp trong ngữ cảnh phiên và dữ liệu thống kê kèm theo.

CÁC QUY TẮC BẮT BUỘC:
1. TRUNG THỰC VỚI SỐ LIỆU & XỬ LÝ 0 LƯỢT PHÁT TỰ NHIÊN:
   - Chỉ nêu con số, tên bài hát, nghệ sĩ, album, thể loại và tỷ lệ thực sự có trong dữ liệu được cung cấp. Tuyệt đối không bịa đặt dữ liệu.
   - Khi trong kỳ đang xem có 0 lượt phát, không tìm thấy nghệ sĩ trong lịch sử, hoặc có dữ liệu `zero_data_context`, hãy trả lời tự nhiên, linh hoạt bằng tiếng Việt (không bịa thêm bài hát/lượt phát). Nếu `all_time_user_plays > 0` hoặc `artist_all_time_plays > 0`, hãy khéo léo cho biết kỳ hiện tại chưa có lượt phát nhưng lịch sử rộng hơn có dữ liệu, và mời bạn bấm chọn một mốc thời gian gợi ý ở bên dưới.
2. HIỂU ĐÚNG NGỮ CẢNH THỐNG KÊ MUSICTRACK:
   - Các cụm như "lấy về <nghệ sĩ/thể loại>", "cho tui xem <nghệ sĩ>" luôn mang nghĩa tra cứu số liệu thống kê nghe nhạc trên MusicTrack, TUYỆT ĐỐI KHÔNG hiểu nhầm thành yêu cầu tải file nhạc MP3 hay giới thiệu tải nhạc từ nền tảng khác.
   - Tập trung trả lời thẳng câu hỏi hiện tại; không liệt kê lan man các chỉ số không liên quan.
   - Tận dụng bộ nhớ cố định của phiên (persistent memory) và lịch sử hội thoại để nhớ phạm vi thời gian, nghệ sĩ/thể loại đang thảo luận và yêu cầu trình bày của người dùng xuyên suốt cả phiên dài.
3. PHÂN BIỆT RÕ BẢN CHẤT SỐ LIỆU:
   - Nêu rõ khoảng thời gian đang phân tích (ví dụ: Năm 2026, Tháng 10/2026, 01/10/2026 - 31/10/2026...).
   - Khi nhắc đến thời lượng nghe, nói rõ là ước tính theo độ dài chuẩn các bài hát đã phát.
   - Khi nhắc đến Audio Features hoặc thể loại nhạc, ghi chú ngắn gọn đó là kết quả phân loại/đo lường của hệ thống MusicTrack.
   - Với AI Music Persona hoặc lời khuyên, nêu rõ đó là phần tổng hợp diễn giải của AI.
4. CÔNG CỤ TỰ CẬP NHẬT BỘ NHỚ PHIÊN (TÙY CHỌN):
   - Khi người dùng nêu sở thích/cách trình bày muốn ghi nhớ trong phiên (ví dụ "nhớ giúp tui thích xem dạng bảng", "trả lời ngắn gọn thôi"), hoặc yêu cầu quên/đặt lại một thông tin đang theo dõi, bạn CÓ THỂ gắn ở cuối cùng (sau câu trả lời) một khối JSON:
     <memory_ops>[{"action":"set|add|update|delete","field":"user_preferences|pinned_facts|active_artist|active_genre|active_track|active_period","key":"...","value":"..."}]</memory_ops>
   - Chỉ xuất khối này khi thực sự cần thêm/sửa/xóa bộ nhớ; hệ thống sẽ tự tách và ẩn khối này trước khi hiển thị cho người dùng.
5. TRÌNH BÀY SẠCH & KHÔNG LỘ THẺ HỆ THỐNG:
   - Tuyệt đối KHÔNG nhắc đến tên thẻ kỹ thuật nội bộ như `<music_data>`, `<conversation_history>`, `<session_memory>`, `<session_persistent_memory>`, `<memory_ops>` hay từ "JSON" trong phần văn bản trả lời người dùng. Hãy diễn đạt tự nhiên là "dữ liệu lịch sử nghe của bạn".
   - Dùng định dạng Markdown rõ ràng (in đậm, danh sách hoặc bảng ngắn gọn khi liệt kê từ 3 mục trở lên).
6. KHÔNG SUY DIỄN TÂM LÝ VÔ CĂN CỨ: Chỉ mô tả mẫu hành vi quan sát được.
7. XƯNG HÔ THÂN THIỆN: Xưng hô là "mình" và "bạn".
8. TUYỆT ĐỐI KHÔNG DÙNG EMOJI hoặc icon ký tự ở bất kỳ đâu."""


def _sanitize_music_answer(text: str) -> str:
    """Loai bo emoji va ngan chan ro ri ten the prompt noi bo ra giao dien nguoi dung."""
    cleaned = _EMOJI_REGEX.sub("", text or "")
    cleaned = _INTERNAL_TAG_PHRASE_REGEX.sub("trong lịch sử nghe của bạn", cleaned)
    cleaned = _INTERNAL_TAG_REGEX.sub("dữ liệu lịch sử nghe", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _build_artist_fallback_answer(artist_focus: dict, scope_label: str) -> str:
    """Tao cau tra loi xac dinh tap trung cho 1 nghe si cu the khi LLM offline hoac timeout."""
    overview = artist_focus.get("overview") or {}
    artist_name = overview.get("artist_name") or "nghệ sĩ này"
    start_date = overview.get("start_date") or ""
    end_date = overview.get("end_date") or ""
    period_desc = f"{scope_label} ({start_date} đến {end_date})" if start_date and end_date else scope_label

    if not overview.get("found_artist"):
        return (
            f"Trong lịch sử nghe nhạc của tài khoản bạn hiện chưa ghi nhận lượt phát nào của nghệ sĩ **{artist_name}**. "
            "Bạn hãy kiểm tra lại tên nghệ sĩ hoặc bấm Đồng bộ Spotify để cập nhật lịch sử mới nhất."
        )

    total_plays = int(overview.get("total_plays") or 0)
    if total_plays == 0:
        return (
            f"Trong khoảng thời gian **{period_desc}**, bạn có **0 lượt phát** của nghệ sĩ **{artist_name}**. "
            "Bạn có thể hỏi mở rộng sang khoảng thời gian khác để xem lịch sử nghe nghệ sĩ này."
        )

    lines = [
        f"## Tổng hợp về {artist_name} ({scope_label})",
        f"Trong giai đoạn **{period_desc}**, bạn đã nghe **{artist_name}** tổng cộng **{total_plays:,} lượt phát** "
        f"(chiếm **{overview.get('share_percentage', 0)}%** tổng lượt phát trong kỳ, gồm {overview.get('unique_tracks_count', 0)} bài hát khác nhau). "
        f"Thời lượng nghe ước tính từ độ dài chuẩn các bản nhạc đạt khoảng **{overview.get('estimated_duration_label', '0 phút')}**.",
    ]

    top_track_name = overview.get("top_track_name")
    top_track_plays = int(overview.get("top_track_plays") or 0)
    if top_track_name:
        lines.append(
            f"- Bài hát nghe nhiều nhất của **{artist_name}**: **{top_track_name}** với **{top_track_plays:,} lượt phát**."
        )

    top_tracks_block = artist_focus.get("top_tracks") or {}
    tracks = top_tracks_block.get("tracks") or []
    if len(tracks) >= 2:
        table_lines = [
            "### Top bài hát của nghệ sĩ trong kỳ",
            "",
            "| Hạng | Bài hát | Lượt phát | Thời lượng ước tính |",
            "|---:|---|---:|---:|",
        ]
        for idx, trk in enumerate(tracks[:5], start=1):
            table_lines.append(
                f"| {idx} | {trk['name']} | {trk['play_count']:,} | {trk.get('estimated_duration_label', '-')} |"
            )
        lines.append("\n".join(table_lines))

    habits = artist_focus.get("habits") or {}
    if habits.get("peak_hour_window") or habits.get("peak_day"):
        habit_parts = []
        if habits.get("peak_hour_window"):
            habit_parts.append(f"khung giờ cao điểm **{habits['peak_hour_window']}** ({habits.get('peak_hour_plays', 0)} lượt)")
        if habits.get("peak_day"):
            habit_parts.append(f"ngày nghe nhiều nhất **{habits['peak_day']}** ({habits.get('peak_day_plays', 0)} lượt)")
        lines.append(f"- Thói quen nghe {artist_name}: {', '.join(habit_parts)}.")

    comp = artist_focus.get("comparison") or {}
    if comp:
        if comp.get("baseline_status") == "new_activity":
            lines.append(
                f"- So với kỳ liền trước ({comp.get('previous_start_date')} đến {comp.get('previous_end_date')}, 0 lượt): đây là hoạt động nghe mới với {artist_name}."
            )
        elif comp.get("growth_percentage") is not None:
            g = comp["growth_percentage"]
            sign = "+" if g > 0 else ""
            lines.append(
                f"- So với kỳ liền trước ({comp.get('previous_plays', 0):,} lượt): mức thay đổi là **{sign}{g}%**."
            )

    return "\n\n".join(lines)


def _build_genre_fallback_answer(genre_focus: dict, scope_label: str) -> str:
    """Tao cau tra loi xac dinh tap trung cho 1 the loai cu the khi LLM offline hoac 0 luot."""
    overview = genre_focus.get("overview") or {}
    genre_name = overview.get("genre_name") or "thể loại này"
    start_date = overview.get("start_date") or ""
    end_date = overview.get("end_date") or ""
    period_desc = f"{scope_label} ({start_date} đến {end_date})" if start_date and end_date else scope_label
    total_plays = int(overview.get("total_plays") or 0)

    if total_plays == 0:
        return (
            f"Trong khoảng thời gian **{period_desc}**, hệ thống chưa ghi nhận lượt phát nào thuộc thể loại **{genre_name}** (0 lượt phát). "
            "Lưu ý: thể loại được xác định bằng bộ phân loại kết hợp của MusicTrack."
        )

    lines = [
        f"## Phân tích thể loại {genre_name} ({scope_label})",
        f"Trong giai đoạn **{period_desc}**, bạn có **{total_plays:,} lượt phát** thuộc thể loại **{genre_name}** "
        f"(chiếm **{overview.get('share_percentage', 0)}%** tổng lượt phát trong kỳ, trải trên {overview.get('unique_artists_count', 0)} nghệ sĩ và {overview.get('unique_tracks_count', 0)} bài hát). "
        f"Thời lượng nghe ước tính đạt khoảng **{overview.get('estimated_duration_label', '0 phút')}**.",
    ]

    top_artists_block = genre_focus.get("top_artists") or {}
    artists = top_artists_block.get("artists") or []
    if artists:
        lead = artists[0]
        lines.append(
            f"- Nghệ sĩ nổi bật nhất trong **{genre_name}**: **{lead['name']}** với **{lead['play_count']:,} lượt phát** ({lead.get('share_in_genre', 0)}% trong thể loại này)."
        )
        if len(artists) >= 2:
            table_lines = [
                f"### Top nghệ sĩ thuộc {genre_name}",
                "",
                "| Hạng | Nghệ sĩ | Lượt phát | Tỷ trọng trong thể loại |",
                "|---:|---|---:|---:|",
            ]
            for idx, art in enumerate(artists[:5], start=1):
                table_lines.append(
                    f"| {idx} | {art['name']} | {art['play_count']:,} | {art.get('share_in_genre', 0)}% |"
                )
            lines.append("\n".join(table_lines))

    top_tracks_block = genre_focus.get("top_tracks") or {}
    tracks = top_tracks_block.get("tracks") or []
    if tracks:
        t_lead = tracks[0]
        lines.append(
            f"- Bài hát nghe nhiều nhất thuộc **{genre_name}**: **{t_lead['name']}** ({', '.join(t_lead.get('artists') or ['Nghệ sĩ'])}) với **{t_lead['play_count']:,} lượt phát**."
        )

    lines.append(
        "> Lưu ý: Phân loại thể loại được tính bằng hệ thống kết hợp của MusicTrack (siêu dữ liệu nghệ sĩ và đặc trưng âm thanh)."
    )
    return "\n\n".join(lines)


def _build_music_fallback_answer(aggregates: dict, scope_label: str) -> str:
    """Tao cau tra loi tieng Viet xac dinh dung trong tam cac tool da goi khi LLM offline hoac timeout."""
    artist_focus = aggregates.get("artist_focus")
    if isinstance(artist_focus, dict) and artist_focus.get("overview"):
        return _build_artist_fallback_answer(artist_focus, scope_label)

    genre_focus = aggregates.get("genre_focus")
    if isinstance(genre_focus, dict) and genre_focus.get("overview"):
        return _build_genre_fallback_answer(genre_focus, scope_label)

    summary = aggregates.get("summary") or {}
    total_plays = int(summary.get("total_plays") or 0)
    unique_tracks = int(summary.get("unique_tracks_count") or 0)
    unique_artists = int(summary.get("unique_artists_count") or 0)
    unique_albums = int(summary.get("unique_albums_count") or 0)
    duration_label = summary.get("estimated_duration_label") or "0 phút"

    if total_plays == 0:
        return (
            f"Trong phạm vi **{scope_label}**, hệ thống chưa ghi nhận lượt phát nào của bạn (0 lượt phát). "
            "Bạn hãy thử chọn một kỳ thời gian khác trên bảng phân tích hoặc bấm Đồng bộ để cập nhật lịch sử nghe mới nhất."
        )

    lines: list[str] = []
    has_specialized = any(
        k in aggregates
        for k in (
            "top_artists",
            "top_tracks",
            "top_albums",
            "genres",
            "audio_features",
            "listening_patterns",
            "knn_recommendations",
            "latest_persona",
        )
    )

    if not has_specialized or "previous_period_plays" in summary:
        lines.append(
            f"Trong phạm vi **{scope_label}**, dữ liệu thực tế ghi nhận bạn có **{total_plays:,} lượt phát** "
            f"trên {unique_tracks:,} bài hát khác nhau, {unique_artists:,} nghệ sĩ và {unique_albums:,} album. "
            f"Thời lượng nghe ước tính (cộng dồn độ dài chuẩn các bản nhạc đã phát) đạt khoảng **{duration_label}**."
        )

    if "previous_period_plays" in summary:
        prev_plays = int(summary.get("previous_period_plays") or 0)
        growth = summary.get("growth_percentage")
        baseline_status = summary.get("baseline_status")
        prev_label = summary.get("previous_period_label") or "kỳ trước"
        if baseline_status == "new_activity":
            lines.append(f"- So với {prev_label} (0 lượt): Đây là hoạt động nghe nhạc mới của bạn trong kỳ này.")
        elif growth is not None:
            sign = "+" if growth > 0 else ""
            lines.append(f"- So với {prev_label} ({prev_plays:,} lượt): Mức thay đổi là **{sign}{growth}%**.")

    top_artists = aggregates.get("top_artists") or []
    if top_artists:
        lead = top_artists[0]
        if not lines:
            lines.append(
                f"Trong phạm vi **{scope_label}**, nghệ sĩ bạn nghe nhiều nhất là **{lead['name']}** "
                f"với **{lead['play_count']:,} lượt phát** (chiếm {lead.get('share_percentage', 0)}% tổng lượt phát kỳ này)."
            )
        else:
            artist_str = ", ".join(f"{a['name']} ({a['play_count']} lượt)" for a in top_artists[:3])
            lines.append(f"- Top nghệ sĩ nổi bật: {artist_str}.")

    top_tracks = aggregates.get("top_tracks") or []
    if top_tracks:
        track_str = ", ".join(f"{t['name']} ({t['play_count']} lượt)" for t in top_tracks[:3])
        if not lines:
            lines.append(f"Trong phạm vi **{scope_label}**, top bài hát bạn nghe nhiều nhất là: {track_str}.")
        else:
            lines.append(f"- Top bài hát nghe nhiều nhất: {track_str}.")

    top_albums = aggregates.get("top_albums") or []
    if top_albums:
        alb_str = ", ".join(f"{al['name']} ({al['play_count']} lượt)" for al in top_albums[:3])
        lines.append(f"- Top album nổi bật trong **{scope_label}**: {alb_str}.")

    genres_block = aggregates.get("genres") or {}
    genres_list = genres_block.get("distribution") or []
    if genres_list:
        genre_str = ", ".join(f"{g['name']} ({g['percentage']}%)" for g in genres_list[:3])
        lines.append(f"- Phân bố thể loại trong **{scope_label}** (theo bộ phân loại kết hợp của MusicTrack): {genre_str}.")

    audio_block = aggregates.get("audio_features") or {}
    highest = audio_block.get("highest_trait")
    prov = audio_block.get("provenance") or {}
    if highest:
        measured_pct = prov.get("measured_percentage", 0.0)
        lines.append(
            f"- Đặc trưng âm thanh nổi bật nhất trong **{scope_label}** là **{highest['attribute']}** ({round(highest['score'] * 100)}%). "
            f"Nguồn gốc chỉ số: {measured_pct}% lượt phát được đo từ dữ liệu âm thanh, phần còn lại có thể là ước lượng hoặc chưa đủ thông số."
        )

    patterns = aggregates.get("listening_patterns") or {}
    peak_windows = patterns.get("peak_windows") or []
    if peak_windows:
        lines.append(f"- Khung giờ nghe nổi bật trong **{scope_label}**: {', '.join(peak_windows[:2])}.")

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

    def _try_openai_compatible_music(self, messages: list[dict[str, str]]) -> tuple[str | None, str, str]:
        config = get_openai_compatible_config()
        if not config.is_configured:
            return None, "", ""
        try:
            client = OpenAICompatibleClient(config)
            for model_name in config.model_candidates:
                try:
                    res = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0.25,
                        max_tokens=800,
                    )
                    txt = strip_reasoning_blocks(res.choices[0].message.content or "")
                    if txt:
                        return txt, "openai_compatible", model_name
                except Exception as exc:
                    logger.warning("Assistant OpenAI-compatible %s that bai: %s", model_name, exc)
        except Exception as exc:
            logger.warning("Khong the khoi tao OpenAI-compatible client: %s", exc)
        return None, "", ""

    def _try_groq_music(self, messages: list[dict[str, str]]) -> tuple[str | None, str, str]:
        groq_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        if not groq_key:
            return None, "", ""
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
                        max_tokens=800,
                    )
                    txt = strip_reasoning_blocks(res.choices[0].message.content or "")
                    if txt:
                        return txt, "groq", model_name
                except Exception as exc:
                    logger.warning("Assistant Groq %s that bai: %s", model_name, exc)
        except Exception as exc:
            logger.warning("Khong the khoi tao Groq client: %s", exc)
        return None, "", ""

    def _try_gemini_music(self, user_payload: str) -> tuple[str | None, str, str]:
        gemini_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            return None, "", ""
        configured_gemini = getattr(settings, "AI_MODEL_GEMINI", "") or os.getenv("AI_MODEL_GEMINI", "")
        gem_models = []
        for m in (configured_gemini, "gemini-2.5-flash", "gemini-1.5-flash"):
            if m and m not in gem_models:
                gem_models.append(m)
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt_text = f"{MUSIC_GROUNDING_SYSTEM_PROMPT}\n\n{user_payload}"
            for gem_model in gem_models:
                try:
                    res = client.models.generate_content(model=gem_model, contents=prompt_text)
                    txt = strip_reasoning_blocks(getattr(res, "text", "") or "")
                    if txt:
                        return txt, "gemini", gem_model
                except Exception as exc:
                    logger.warning("Assistant Gemini %s that bai: %s", gem_model, exc)
        except Exception as exc:
            logger.warning("Khong the khoi tao Gemini client: %s", exc)
        return None, "", ""

    def _synthesize_music_with_llm_and_ops(
        self,
        query_text: str,
        aggregates: dict,
        recent_turns: list[dict],
        compressed_memory: str = "",
        active_entities: dict | None = None,
        persistent_memory_markdown: str = "",
    ) -> tuple[str | None, list[dict], str, str]:
        """Goi LLM voi day du 2 lop bo nho (Persistent Memory + Episodic Memory) va tach <memory_ops>."""
        compact_turns = [
            {
                "scope": t.get("scope_label", ""),
                "user": t.get("query", ""),
                "assistant_summary": t.get("answer_summary", ""),
            }
            for t in recent_turns[-6:]
        ]

        sections = []
        if persistent_memory_markdown:
            sections.append(
                f"<session_persistent_memory>\n{persistent_memory_markdown}\n</session_persistent_memory>"
            )
        if compressed_memory:
            sections.append(f"<session_memory>\n{compressed_memory}\n</session_memory>")
        if active_entities:
            sections.append(
                "<active_entities>\n"
                + json.dumps(active_entities, ensure_ascii=False)
                + "\n</active_entities>"
            )
        sections.append(
            "<conversation_history>\n"
            + json.dumps(compact_turns, ensure_ascii=False)
            + "\n</conversation_history>"
        )
        sections.append(
            "<music_data>\n"
            + json.dumps(aggregates, ensure_ascii=False)
            + "\n</music_data>"
        )
        sections.append(
            f"Câu hỏi hiện tại của bạn: {query_text}\n"
            "Hãy trả lời đúng trọng tâm, trung thực theo số liệu lịch sử nghe của người dùng, "
            "nêu rõ khoảng thời gian, phân biệt ước tính/thực tế và tuyệt đối không nhắc tên các thẻ hệ thống."
        )
        user_payload = "\n\n".join(sections)

        messages = [
            {"role": "system", "content": MUSIC_GROUNDING_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ]

        runners = {
            "openai_compatible": lambda: self._try_openai_compatible_music(messages),
            "groq": lambda: self._try_groq_music(messages),
            "gemini": lambda: self._try_gemini_music(user_payload),
        }
        for provider_key in get_ai_provider_order():
            raw_txt, provider_used, model_used = runners[provider_key]()
            if raw_txt:
                stripped_txt, agent_ops = extract_and_strip_memory_ops(raw_txt)
                clean_txt = _sanitize_music_answer(stripped_txt)
                if clean_txt:
                    return clean_txt, agent_ops, provider_used, model_used

        return None, [], "local_music_synthesizer", "deterministic_music_v1"

    def _synthesize_music_with_llm(
        self,
        query_text: str,
        aggregates: dict,
        recent_turns: list[dict],
        compressed_memory: str = "",
        active_entities: dict | None = None,
        persistent_memory_markdown: str = "",
    ) -> tuple[str | None, str, str]:
        """Wrapper tuong thich nguoc tra ve 3-tuple (answer, provider_used, model_used)."""
        clean_txt, _, provider_used, model_used = self._synthesize_music_with_llm_and_ops(
            query_text=query_text,
            aggregates=aggregates,
            recent_turns=recent_turns,
            compressed_memory=compressed_memory,
            active_entities=active_entities,
            persistent_memory_markdown=persistent_memory_markdown,
        )
        return clean_txt, provider_used, model_used

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
        """Xu ly mot luot hoi dap hoan chinh voi co lap User Scope va 2 lop Session Memory."""
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
            total_existing = session_state.get("music_total_turns", 0) + session_state.get("website_total_turns", 0)
            has_any_mem = bool(session_state.get("music_memory") or session_state.get("website_memory"))
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
                    session_turns=total_existing,
                    has_compressed_memory=has_any_mem,
                ),
            )

        # 2. Mien Du lieu Am nhac ca nhan (Music Insights)
        if decision.resolved_domain == "music_insights":
            norm_q = normalize_vi_text(query_text)
            music_ctx = get_domain_context(user.id, session_id, "music_insights")

            if any(trivia in norm_q for trivia in OUT_OF_SCOPE_TRIVIA_CUES):
                return AssistantQueryResult(
                    query=query_text,
                    answer=(
                        "Câu hỏi này nằm ngoài phạm vi dữ liệu âm nhạc cá nhân trên MusicTrack. "
                        "Bạn có thể hỏi về lượt phát, bài hát/nghệ sĩ/album nổi bật, tổng hợp 1 nghệ sĩ hoặc 1 thể loại cụ thể theo khoảng thời gian, "
                        "so sánh giữa các kỳ, chỉ số Audio Features, khung giờ nghe nhạc hoặc gợi ý bài hát tương đồng."
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
                        session_turns=music_ctx["total_turns"],
                        has_compressed_memory=music_ctx["has_compressed_memory"],
                    ),
                )

            bundle = collect_music_insights_bundle(
                user=user,
                query_text=query_text,
                period_context=period_context,
                top_k=top_k,
                session_entities=music_ctx["entities"],
                persistent_memory=music_ctx["persistent_memory"],
            )
            aggregates = bundle["aggregates"]
            scope: AssistantScopeMeta = bundle["scope"]
            artist_overview = (aggregates.get("artist_focus") or {}).get("overview")
            genre_overview = (aggregates.get("genre_focus") or {}).get("overview")

            llm_answer, agent_memory_ops, provider_used, model_name = self._synthesize_music_with_llm_and_ops(
                query_text=query_text,
                aggregates=aggregates,
                recent_turns=music_ctx["turns"],
                compressed_memory=music_ctx["compressed_memory"],
                active_entities=music_ctx["entities"],
                persistent_memory_markdown=music_ctx["persistent_memory_markdown"],
            )
            if llm_answer:
                answer = llm_answer
                is_fallback = False
            else:
                answer = _build_music_fallback_answer(aggregates, scope.label)
                is_fallback = True

            # Cap nhat Session Persistent Memory: nen xac thuc tu DB truoc, sau do ap dung lenh CRUD tu Agent
            tools_used = list(bundle["tools_used"])
            baseline_ops = list(bundle.get("memory_baseline_ops") or [])
            if baseline_ops:
                tool_update_session_memory(user.id, session_id, "music_insights", baseline_ops)
            if agent_memory_ops:
                agent_mem_res = tool_update_session_memory(
                    user.id, session_id, "music_insights", agent_memory_ops
                )
                if agent_mem_res.get("applied", 0) > 0:
                    tools_used.append("session_memory_update")

            saved = append_domain_turn(
                user_id=user.id,
                session_id=session_id,
                domain="music_insights",
                user_query=query_text,
                answer_text=answer,
                scope_label=scope.label,
                entities=bundle.get("detected_entities"),
            )

            if isinstance(artist_overview, dict) and artist_overview.get("artist_name"):
                topic_title = f"Phân tích nghệ sĩ {artist_overview['artist_name']} ({scope.label})"
            elif isinstance(genre_overview, dict) and genre_overview.get("genre_name"):
                topic_title = f"Phân tích thể loại {genre_overview['genre_name']} ({scope.label})"
            else:
                topic_title = f"Dữ liệu cá nhân kỳ: {scope.label}"

            return AssistantQueryResult(
                query=query_text,
                answer=answer,
                active_mode=mode,
                resolved_domain="music_insights",
                needs_clarification=False,
                clarification_options=[],
                suggested_scopes=bundle.get("suggested_scopes", []),
                scope=scope,
                evidence=bundle["evidence"],
                topics=[
                    AssistantTopicItem(
                        id="music-scope",
                        title=topic_title,
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
                    tools_used=tools_used,
                    session_turns=saved["total_turns"],
                    has_compressed_memory=saved["has_compressed_memory"],
                ),
            )

        # 3. Mien Ho tro Website (Website Support RAG)
        website_ctx = get_domain_context(user.id, session_id, "website_support")
        ws_res = query_website_support(
            query_text=query_text,
            is_staff=is_staff,
            rag_mode_str=rag_mode,
            top_k=top_k,
            use_cache=use_cache,
            website_turns=website_ctx["turns"],
            compressed_memory=website_ctx["compressed_memory"],
        )
        saved = append_domain_turn(
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
                session_turns=saved["total_turns"],
                has_compressed_memory=saved["has_compressed_memory"],
            ),
        )


_assistant_singleton: HybridAssistantService | None = None


def get_assistant_service() -> HybridAssistantService:
    """Tra ve singleton cua HybridAssistantService."""
    global _assistant_singleton
    if _assistant_singleton is None:
        _assistant_singleton = HybridAssistantService()
    return _assistant_singleton
