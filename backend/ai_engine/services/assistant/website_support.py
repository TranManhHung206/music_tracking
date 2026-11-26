"""
Lop Website Support RAG cho Hybrid Assistant.
Bao toan pipeline Full Cascade va che giau chi tiet noi bo cho nguoi dung pho thong.
"""

import re
import logging
from ai_engine.services.rag.service import get_rag_service
from ai_engine.services.rag.retrieval.cascade import PipelineMode
from ai_engine.services.rag.grounding.prompt_builder import ESCAPE_HATCH_PHRASE
from .security_guard import SECURITY_REFUSAL_MESSAGE, redact_or_block_sensitive_output
from .schemas import (
    AssistantScopeMeta,
    AssistantTopicItem,
)

logger = logging.getLogger(__name__)

_TOPIC_MAPPING: list[tuple[str, str, str]] = [
    ("users/", "Xác thực Spotify & Bảo mật tài khoản", "Tài khoản & Bảo mật"),
    ("tracker/", "Đồng bộ lịch sử nghe nhạc (Auto-Scrobble)", "Đồng bộ dữ liệu"),
    ("analytics/", "Thống kê & Biểu đồ Phân tích Âm nhạc", "Phân tích Dashboard"),
    ("ai_engine/services/ai_persona", "AI Music Persona & Phân tích Tâm lý", "Trí tuệ nhân tạo"),
    ("ai_engine/services/knn_recommender", "Hệ thống Gợi ý Bài hát Tương đồng (KNN)", "Gợi ý âm nhạc"),
    ("ai_engine/services/facts_agent", "AI Music Detective & Phát hiện Xu hướng", "Trí tuệ nhân tạo"),
    ("ai_engine/services/rag", "Trợ lý Hỗ trợ Sử dụng Website", "Hướng dẫn"),
    ("ai_engine/services/assistant", "Trợ lý Lai MusicTrack Assistant", "Hướng dẫn"),
    ("frontend/", "Giao diện & Trải nghiệm Dashboard", "Giao diện người dùng"),
    ("README.md", "Hướng dẫn sử dụng & Tổng quan MusicTrack", "Tài liệu sản phẩm"),
]

_INTERNAL_PATH_REGEX = re.compile(r"`(?:backend|frontend)/[^`]+`")
_CITATION_TOKEN_REGEX = re.compile(r"\s*\[(?:S|C)\d+\]")


def map_citation_to_topic(file_path: str) -> tuple[str, str]:
    """Chuyen doi duong dan noi bo sang ten chu de huong dan than thien."""
    normalized = (file_path or "").replace("\\", "/").lstrip("/")
    for prefix, title, category in _TOPIC_MAPPING:
        if prefix in normalized:
            return title, category
    return "Tài liệu Hướng dẫn MusicTrack", "Tài liệu chung"


def _build_topics_from_citations(citations: list[dict]) -> list[AssistantTopicItem]:
    seen_titles: set[str] = set()
    topics: list[AssistantTopicItem] = []
    for idx, cit in enumerate(citations, start=1):
        title, category = map_citation_to_topic(str(cit.get("file_path") or ""))
        if title in seen_titles:
            continue
        seen_titles.add(title)
        topics.append(
            AssistantTopicItem(
                id=f"topic-{idx}",
                title=title,
                category=category,
            )
        )
    return topics


def _sanitize_answer_for_end_user(answer: str) -> str:
    cleaned = _CITATION_TOKEN_REGEX.sub("", answer or "")
    cleaned = _INTERNAL_PATH_REGEX.sub("tài liệu hệ thống", cleaned)
    cleaned = re.sub(r"[ \t]+\.", ".", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    safe_cleaned, _ = redact_or_block_sensitive_output(cleaned)
    return safe_cleaned


def _maybe_enrich_followup_query(
    query_text: str,
    website_turns: list[dict],
    compressed_memory: str = "",
) -> str:
    """Bo sung ngu canh Website Support tu luot gan nhat hoac bo nho nen khi gap cau hoi noi tiep."""
    if not website_turns and not compressed_memory:
        return query_text
    tokens = query_text.strip().split()
    lowered = query_text.lower()
    followup_hints = (
        "chi tiết hơn",
        "rõ hơn",
        "phần đó",
        "cơ chế đó",
        "còn sao",
        "như thế nào nữa",
        "cái đó",
        "tính năng đó",
        "về điều đó",
        "nhắc lại",
        "lúc nãy",
        "trước đó",
    )
    if len(tokens) <= 9 and any(h in lowered for h in followup_hints):
        if website_turns:
            last_q = str(website_turns[-1].get("query") or "").strip()
            if last_q:
                return f"{last_q} - {query_text}"
        if compressed_memory:
            last_mem_line = [ln.strip() for ln in compressed_memory.splitlines() if ln.strip()][-1]
            return f"{last_mem_line[:160]} - {query_text}"
    return query_text


def query_website_support(
    query_text: str,
    is_staff: bool = False,
    rag_mode_str: str = "full_cascade",
    top_k: int = 5,
    use_cache: bool = True,
    website_turns: list[dict] | None = None,
    compressed_memory: str = "",
) -> dict:
    """
    Thuc thi truy van Website Support qua CodebaseRAGService,
    an toan hoa dau ra theo quyen is_staff.
    """
    effective_mode = PipelineMode.FULL_CASCADE
    if is_staff:
        try:
            effective_mode = PipelineMode(rag_mode_str)
        except ValueError:
            effective_mode = PipelineMode.FULL_CASCADE

    effective_query = _maybe_enrich_followup_query(
        query_text,
        website_turns or [],
        compressed_memory=compressed_memory,
    )

    try:
        rag_service = get_rag_service()
        rag_res = rag_service.query(
            query_text=effective_query,
            mode=effective_mode,
            final_k=top_k,
            use_cache=use_cache,
        )
        raw_dump = rag_res.model_dump()
    except Exception as exc:
        logger.warning("Website Support RAG khong kha dung: %s", exc)
        return {
            "answer": (
                "Hệ thống tra cứu tài liệu hướng dẫn hiện tạm thời gián đoạn kết nối. "
                "Bạn có thể thử lại sau ít phút hoặc chuyển sang chế độ Dữ liệu Âm nhạc để xem số liệu cá nhân."
            ),
            "scope": AssistantScopeMeta(
                label="Tài liệu Website MusicTrack",
                source="website_docs",
                note="Dịch vụ tra cứu tài liệu hiện đang tạm gián đoạn.",
            ),
            "topics": [],
            "dev_citations": [],
            "dev_verification": None,
            "dev_metrics": None,
            "provider_used": "website_rag_unavailable",
            "model_name": "unavailable",
            "is_fallback": True,
            "tools_used": ["website_rag"],
        }

    raw_citations = list(raw_dump.get("citations") or [])
    raw_verification = dict(raw_dump.get("verification") or {})
    raw_answer = str(raw_dump.get("answer") or "").strip() or ESCAPE_HATCH_PHRASE
    blocked_by_security = bool(raw_verification.get("blocked_by_security_guard"))
    is_escape_hatch = bool(raw_verification.get("is_escape_hatch")) or (
        ESCAPE_HATCH_PHRASE.lower() in raw_answer.lower()
    )

    final_answer = raw_answer if is_staff else _sanitize_answer_for_end_user(raw_answer)
    safe_answer, out_blocked = redact_or_block_sensitive_output(final_answer)
    if blocked_by_security or out_blocked:
        final_answer = SECURITY_REFUSAL_MESSAGE if blocked_by_security else safe_answer
        topics = []
        raw_citations = []
        scope_label = "Từ chối vì lý do bảo mật"
        scope_note = "Nội dung bị chặn để bảo vệ an toàn cấu hình hệ thống."
    else:
        topics = [] if is_escape_hatch else _build_topics_from_citations(raw_citations)
        scope_label = "Tài liệu Website MusicTrack"
        scope_note = (
            "Không tìm thấy thông tin khớp trong tài liệu sản phẩm."
            if is_escape_hatch
            else "Dựa trên tài liệu và hướng dẫn sử dụng chính thức của MusicTrack."
        )

    result = {
        "answer": final_answer,
        "scope": AssistantScopeMeta(
            label=scope_label,
            source="website_docs",
            note=scope_note,
        ),
        "topics": topics,
        "dev_citations": raw_citations if is_staff else [],
        "dev_verification": raw_verification if is_staff else None,
        "dev_metrics": (
            {
                "latency_ms": raw_dump.get("latency_ms", 0.0),
                "retrieved_chunks_count": raw_dump.get("retrieved_chunks_count", 0),
                "rag_mode": effective_mode.value,
            }
            if is_staff
            else None
        ),
        "provider_used": "codebase_rag",
        "model_name": f"rag_{effective_mode.value}",
        "is_fallback": is_escape_hatch and len(raw_citations) == 0,
        "tools_used": ["codebase_rag"],
    }
    return result
