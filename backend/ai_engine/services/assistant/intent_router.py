"""
Bo dinh tuyen y dinh (Intent Router) cho Hybrid Music & Website Assistant.
Phan tach ranh gioi giua Music Insights, Website Support va cau hoi mo ho can lam ro.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from .schemas import AssistantModeLiteral, ResolvedDomainLiteral

WEBSITE_STRONG_PHRASES = (
    ("cach hoat dong", 4),
    ("hoat dong nhu the nao", 4),
    ("hoat dong the nao", 4),
    ("hoat dong sao", 4),
    ("co che", 4),
    ("tinh nang", 3),
    ("website nay", 4),
    ("trang web nay", 4),
    ("ung dung nay", 4),
    ("he thong", 3),
    ("chong trung", 4),
    ("khong ghi nhan trung", 4),
    ("deduplicat", 4),
    ("auto-scrobble", 4),
    ("auto scrobble", 4),
    ("dong bo", 3),
    ("bao mat", 4),
    ("quyen rieng tu", 4),
    ("tai khoan spotify", 4),
    ("token", 4),
    ("luu tru", 3),
    ("ma hoa", 4),
    ("fernet", 4),
    ("oauth", 4),
    ("pkce", 4),
    ("rate limit", 4),
    ("429", 3),
    ("celery", 4),
    ("redis", 4),
    ("demo mode", 4),
    ("che do xem thu", 4),
    ("che do demo", 4),
    ("duoc bao ve", 4),
    ("bao ve nhu the nao", 4),
    ("bao ve the nao", 4),
    ("dua vao nhung yeu to", 4),
    ("dua vao yeu to nao", 4),
    ("thuat toan", 4),
    ("kien truc", 4),
    ("rag", 4),
    ("su dung website", 4),
    ("bieu do nay la gi", 4),
    ("chi so nay co nghia", 4),
)

WEBSITE_MEDIUM_PHRASES = (
    ("knn", 2),
    ("dang nhap", 2),
    ("dang xuat", 2),
    ("cach dung", 2),
    ("huong dan", 2),
    ("lam the nao", 2),
    ("nhu the nao", 2),
    ("tai sao he thong", 3),
    ("api", 2),
)

MUSIC_STRONG_PHRASES = (
    ("cua toi", 4),
    ("cua minh", 4),
    ("cua tui", 4),
    ("toi nghe", 4),
    ("minh nghe", 4),
    ("tui nghe", 4),
    ("cho toi", 3),
    ("cho minh", 3),
    ("cho tui", 3),
    ("tuan nay", 4),
    ("tuan truoc", 4),
    ("thang nay", 4),
    ("thang truoc", 4),
    ("nam nay", 4),
    ("nam truoc", 4),
    ("nam ngoai", 4),
    ("hom nay", 3),
    ("hom qua", 3),
    ("7 ngay", 3),
    ("30 ngay", 3),
    ("nghe nhieu nhat", 4),
    ("top bai hat", 4),
    ("top nghe si", 4),
    ("top album", 4),
    ("gu am nhac", 4),
    ("gu nhac", 4),
    ("luot phat", 3),
    ("luot nghe", 3),
    ("thoi luong nghe", 3),
    ("thoi gian nghe", 3),
    ("bao nhieu bai", 3),
    ("bao nhieu luot", 4),
    ("may lan", 3),
    ("khung gio nghe", 4),
    ("may gio", 3),
    ("cu dem", 4),
    ("goi y cho toi", 4),
    ("goi y cho tui", 4),
    ("goi y bai", 3),
    ("bai nao tuong tu", 4),
    ("giong bai", 4),
    ("so sanh voi ky truoc", 4),
    ("so sanh ky", 4),
    ("tang hay giam", 4),
    ("audio features cua", 3),
    ("nghe si do", 4),
    ("ca si do", 4),
    ("nghe si nay", 4),
    ("ca si nay", 4),
    ("bai hat do", 3),
)

MUSIC_MEDIUM_PHRASES = (
    ("nghe si", 2),
    ("ca si", 2),
    ("bai hat", 2),
    ("album", 2),
    ("the loai", 2),
    ("dong nhac", 2),
    ("v-pop", 2),
    ("vpop", 2),
    ("k-pop", 2),
    ("kpop", 2),
    ("edm", 2),
    ("electronic", 2),
    ("dj", 2),
    ("phonk", 2),
    ("hip-hop", 2),
    ("hiphop", 2),
    ("rap", 2),
    ("lofi", 2),
    ("lo-fi", 2),
    ("valence", 2),
    ("energy", 2),
    ("danceability", 2),
    ("acousticness", 2),
    ("tempo", 2),
    ("radar", 2),
    ("heatmap", 2),
    ("persona", 2),
    ("xu huong", 2),
    ("marathon", 2),
)

FOLLOWUP_ONLY_CUES = (
    "con ky truoc",
    "con thang truoc",
    "con tuan truoc",
    "con nam ngoai",
    "con phan",
    "chi tiet hon",
    "giai thich ro hon",
    "so sanh them",
    "con gi nua",
    "cu the hon",
    "ve dieu do",
    "cai do",
    "no la gi",
    "cua ho",
    "ve ho",
    "cua anh ay",
    "cua co ay",
    "nguoi do",
    "lay ve",
    "xem ve",
    "thong tin ve",
    "the loai do",
    "dong nhac do",
    "nho giup",
    "ghi nho",
    "quen",
)

OUT_OF_SCOPE_TRIVIA_CUES = (
    "thoi tiet",
    "gia vang",
    "chung khoan",
    "ty so bong da",
    "world cup",
    "chinh tri",
    "tong thong",
    "cong thuc nau an",
    "thu do nuoc",
)


def normalize_vi_text(text: str) -> str:
    """Chuan hoa chuoi tieng Viet ve dang khong dau, chu thuong de phan tich y dinh."""
    replaced = (text or "").replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", replaced)
    stripped = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _score_phrases(norm_text: str, weighted_phrases: tuple[tuple[str, int], ...]) -> tuple[int, list[str]]:
    score = 0
    matched: list[str] = []
    for phrase, weight in weighted_phrases:
        if phrase in norm_text:
            score += weight
            matched.append(phrase)
    return score, matched


@dataclass
class IntentRouteDecision:
    resolved_domain: ResolvedDomainLiteral
    needs_clarification: bool
    reason: str
    music_score: int = 0
    website_score: int = 0
    matched_cues: list[str] = field(default_factory=list)
    is_followup: bool = False


def route_assistant_intent(
    query: str,
    requested_mode: AssistantModeLiteral = "auto",
    last_domain: str | None = None,
) -> IntentRouteDecision:
    """
    Xac dinh mien xu ly phu hop dua tren che do nguoi dung chon, tu khoa ngu nghia
    va lich su phien gan nhat.
    """
    if requested_mode == "music_insights":
        return IntentRouteDecision(
            resolved_domain="music_insights",
            needs_clarification=False,
            reason="explicit_music_insights",
        )
    if requested_mode == "website_support":
        return IntentRouteDecision(
            resolved_domain="website_support",
            needs_clarification=False,
            reason="explicit_website_support",
        )

    norm = normalize_vi_text(query)
    if not norm or len(norm) < 2:
        return IntentRouteDecision(
            resolved_domain="clarification",
            needs_clarification=True,
            reason="empty_or_too_short",
        )

    w_strong, w_s_cues = _score_phrases(norm, WEBSITE_STRONG_PHRASES)
    w_med, w_m_cues = _score_phrases(norm, WEBSITE_MEDIUM_PHRASES)
    m_strong, m_s_cues = _score_phrases(norm, MUSIC_STRONG_PHRASES)
    m_med, m_m_cues = _score_phrases(norm, MUSIC_MEDIUM_PHRASES)

    website_score = w_strong + w_med
    music_score = m_strong + m_med

    if any(p in norm for p in ("toi", "minh", "tui")) and m_med > 0 and w_strong == 0:
        music_score += 2
    if re.search(r"\b(?:thang\s+(?:1[0-2]|0?[1-9])|nam\s+20\d{2}|quy\s+[1-4])\b", norm) and w_strong == 0:
        music_score += 2
    if "persona" in norm and any(p in norm for p in ("hoat dong", "tao ra", "co che")):
        website_score += 3
    if "knn" in norm and any(p in norm for p in ("dua vao", "yeu to", "hoat dong", "tinh nhu")):
        website_score += 3

    all_cues = m_s_cues + m_m_cues + w_s_cues + w_m_cues

    if any(trivia in norm for trivia in OUT_OF_SCOPE_TRIVIA_CUES) and music_score < 3 and website_score < 3:
        return IntentRouteDecision(
            resolved_domain="website_support",
            needs_clarification=False,
            reason="out_of_scope_safe_escape_hatch",
            music_score=music_score,
            website_score=website_score,
            matched_cues=all_cues,
        )

    is_short_followup = len(norm.split()) <= 12 and any(cue in norm for cue in FOLLOWUP_ONLY_CUES)

    if music_score >= 3 and website_score >= 3 and abs(music_score - website_score) <= 1:
        return IntentRouteDecision(
            resolved_domain="clarification",
            needs_clarification=True,
            reason="conflicting_dual_intent",
            music_score=music_score,
            website_score=website_score,
            matched_cues=all_cues,
        )

    if music_score > website_score and music_score >= 2:
        return IntentRouteDecision(
            resolved_domain="music_insights",
            needs_clarification=False,
            reason="scored_music_insights",
            music_score=music_score,
            website_score=website_score,
            matched_cues=all_cues,
            is_followup=is_short_followup,
        )

    if website_score > music_score and website_score >= 2:
        return IntentRouteDecision(
            resolved_domain="website_support",
            needs_clarification=False,
            reason="scored_website_support",
            music_score=music_score,
            website_score=website_score,
            matched_cues=all_cues,
            is_followup=is_short_followup,
        )

    if is_short_followup and last_domain in ("music_insights", "website_support"):
        return IntentRouteDecision(
            resolved_domain=last_domain,  # type: ignore[arg-type]
            needs_clarification=False,
            reason="session_followup_continuity",
            music_score=music_score,
            website_score=website_score,
            matched_cues=all_cues,
            is_followup=True,
        )

    return IntentRouteDecision(
        resolved_domain="clarification",
        needs_clarification=True,
        reason="ambiguous_intent",
        music_score=music_score,
        website_score=website_score,
        matched_cues=all_cues,
    )
