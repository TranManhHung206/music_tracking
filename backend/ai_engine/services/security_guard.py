"""
Module phong ve da tang chong Prompt Injection, Jailbreak va ro ri cau hinh nhay cam (.env, API keys, system prompt)
cho MusicTrack Assistant va Codebase RAG.
"""

import re
import unicodedata
from dataclasses import dataclass

SECURITY_REFUSAL_MESSAGE = (
    "Yêu cầu này vi phạm chính sách bảo mật của MusicTrack. Mình không thể thực hiện lệnh ghi đè "
    "chỉ thị hệ thống hoặc cung cấp tệp cấu hình (.env), khóa bí mật, mã xác thực hay hướng dẫn nội bộ. "
    "Bạn có thể hỏi về dữ liệu nghe nhạc cá nhân hoặc cách sử dụng các tính năng trên website."
)

_ZERO_WIDTH_REGEX = re.compile(r"[\u200b-\u200f\ufeff]")

_INTERNAL_MARKUP_REGEX = re.compile(
    r"<\s*/?\s*(?:memory_ops|music_data|code_context|session_persistent_memory|session_memory|active_entities|conversation_history|system)\b[^>]*>",
    flags=re.IGNORECASE,
)

_PROMPT_INJECTION_PATTERNS = (
    re.compile(
        r"\b(?:ignore|disregard|forget|override|bypass|skip)\s+(?:all\s+|any\s+|every\s+|the\s+)?"
        r"(?:previous|prior|above|earlier|system|safety|security)\s+"
        r"(?:instructions?|prompts?|rules?|guidelines?|constraints?|directives?)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:bo\s+qua|quen\s+het|vo\s+hieu\s+hoa|phot\s+lo|ghi\s+de)\s+"
        r"(?:tat\s+ca\s+|moi\s+|toan\s+bo\s+)?(?:chi\s+thi|huong\s+dan|quy\s+tac|lenh|rang\s+buoc)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:jailbreak|dan\s+mode|developer\s+mode|god\s+mode|unrestricted\s+mode|do\s+anything\s+now)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:you\s+are\s+now|act\s+as\s+(?:a\s+)?(?:hacker|root|admin|system\s+shell)|"
        r"pretend\s+(?:you\s+have\s+no|there\s+are\s+no)\s+(?:rules|restrictions))\b",
        flags=re.IGNORECASE,
    ),
)

_SYSTEM_PROMPT_VERBS = (
    r"(?:print|show|reveal|display|dump|repeat|output|leak|expose|give\s+me|tell\s+me|"
    r"in\s+ra|hien\s+thi|xuat\s+ra|cho\s+(?:toi|tui|minh)\s+xem|tiet\s+lo)"
)
_SYSTEM_PROMPT_TARGETS = (
    r"(?:system\s+prompt|hidden\s+prompt|developer\s+prompt|initial\s+instructions?|"
    r"prompt\s+he\s+thong|chi\s+thi\s+he\s+thong)"
)
_SYSTEM_PROMPT_EXTRACTION_REGEX = re.compile(
    rf"\b{_SYSTEM_PROMPT_VERBS}\b.{{0,40}}\b{_SYSTEM_PROMPT_TARGETS}\b",
    flags=re.IGNORECASE,
)
_SYSTEM_PROMPT_CONSTANTS_REGEX = re.compile(
    r"\b(?:grounding_system_prompt|music_grounding_system_prompt)\b",
    flags=re.IGNORECASE,
)

_DOT_ENV_REGEX = re.compile(r"(?<![a-z0-9_])\.env(?:\.[a-z0-9_-]+)?(?![a-z0-9_])", flags=re.IGNORECASE)

_EXFIL_VERBS = (
    r"(?:print|show|cat|read|dump|reveal|output|display|leak|expose|give|tell|"
    r"in\s+ra|doc\s+file|xem\s+file|hien\s+thi|xuat|tiet\s+lo|lay\s+gia\s+tri)"
)
_EXFIL_TARGETS = (
    r"(?:env\s+file|file\s+env|environment\s+variables?|bien\s+moi\s+truong|settings\.py|"
    r"secret_key|fernet_secret_key|spotify_client_secret|groq_api_key|gemini_api_key|"
    r"llm_api_key|openai_api_key|database_url|encrypted_access_token|encrypted_refresh_token|"
    r"access_token|refresh_token|api\s*key|client\s*secret|private\s+key)"
)
_SECRET_EXFIL_REGEX = re.compile(
    rf"\b{_EXFIL_VERBS}\b.{{0,35}}\b{_EXFIL_TARGETS}\b",
    flags=re.IGNORECASE,
)
_SPECIFIC_SECRET_VAR_REGEX = re.compile(
    r"\b(?:secret_key|fernet_secret_key|spotify_client_secret|groq_api_key|gemini_api_key|"
    r"llm_api_key|encrypted_access_token|encrypted_refresh_token)\b",
    flags=re.IGNORECASE,
)
_SPECIFIC_VALUE_ACTION_REGEX = re.compile(
    r"\b(?:print|show|dump|leak|expose|output|in\s+ra|xem|lay|gia\s+tri|value|export)\b",
    flags=re.IGNORECASE,
)

_ENV_ASSIGNMENT_LEAK_REGEX = re.compile(
    r"(?im)^\s*(?:SECRET_KEY|FERNET_SECRET_KEY|SPOTIFY_CLIENT_SECRET|SPOTIFY_CLIENT_ID|"
    r"GROQ_API_KEY|GEMINI_API_KEY|LLM_API_KEY|OPENAI_API_KEY|DATABASE_URL|REDIS_URL|"
    r"CELERY_BROKER_URL)\s*=\s*\S+"
)
_SENSITIVE_SAMPLE_LITERALS = (
    "django_insecure_development_key",
    "your_fernet_256bit_key_base64",
    "your_spotify_client_secret",
    "your_groq_api_key",
    "your_gemini_api_key",
    "your_llm_api_key",
)
_SYSTEM_PROMPT_LEAK_MARKERS = (
    "GROUNDING_SYSTEM_PROMPT",
    "MUSIC_GROUNDING_SYSTEM_PROMPT",
    "CÁC QUY TẮC GIẢI THÍCH BẮT BUỘC",
    "CÔNG CỤ TỰ CẬP NHẬT BỘ NHỚ PHIÊN",
)


@dataclass
class SecurityCheckResult:
    """Ket qua kiem tra an toan dau vao nguoi dung."""

    blocked: bool
    category: str = "none"
    reason: str = ""


def _normalize_for_security(text: str) -> str:
    cleaned = _ZERO_WIDTH_REGEX.sub("", text or "")
    replaced = cleaned.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", replaced)
    stripped = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def strip_prompt_injection_markup(text: str) -> str:
    """Loai bo cac the XML he thong gia mao ben trong du lieu nguoi dung."""
    cleaned = _ZERO_WIDTH_REGEX.sub("", text or "")
    cleaned = _INTERNAL_MARKUP_REGEX.sub(" ", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def inspect_user_query_security(query_text: str) -> SecurityCheckResult:
    """Phat hien Prompt Injection, trich xuat System Prompt hoac do .env/khoa bi mat."""
    raw = _ZERO_WIDTH_REGEX.sub("", query_text or "")
    if not raw.strip():
        return SecurityCheckResult(blocked=False)

    if _INTERNAL_MARKUP_REGEX.search(raw):
        return SecurityCheckResult(
            blocked=True,
            category="markup_injection",
            reason="detected_internal_xml_tag",
        )

    norm = _normalize_for_security(raw)

    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern.search(norm):
            return SecurityCheckResult(
                blocked=True,
                category="prompt_injection",
                reason="detected_instruction_override",
            )

    if _SYSTEM_PROMPT_CONSTANTS_REGEX.search(norm) or _SYSTEM_PROMPT_EXTRACTION_REGEX.search(norm):
        return SecurityCheckResult(
            blocked=True,
            category="system_prompt_extraction",
            reason="detected_system_prompt_probe",
        )

    if _DOT_ENV_REGEX.search(norm) or _SECRET_EXFIL_REGEX.search(norm):
        return SecurityCheckResult(
            blocked=True,
            category="secret_exfiltration",
            reason="detected_env_or_secret_probe",
        )

    if _SPECIFIC_SECRET_VAR_REGEX.search(norm) and _SPECIFIC_VALUE_ACTION_REGEX.search(norm):
        return SecurityCheckResult(
            blocked=True,
            category="secret_exfiltration",
            reason="detected_secret_variable_probe",
        )

    return SecurityCheckResult(blocked=False)


def contains_sensitive_leak(text: str) -> bool:
    """Kiem tra xem van ban co chua dong gan bien .env nhay cam hoac lo System Prompt khong."""
    content = text or ""
    if not content.strip():
        return False

    if _ENV_ASSIGNMENT_LEAK_REGEX.search(content):
        return True

    lowered = content.lower()
    if any(literal in lowered for literal in _SENSITIVE_SAMPLE_LITERALS):
        return True

    if any(marker in content for marker in _SYSTEM_PROMPT_LEAK_MARKERS):
        return True

    return False


def redact_or_block_sensitive_output(text: str) -> tuple[str, bool]:
    """Chan va thay the toan bo phan hoi neu phat hien ro ri .env hoac System Prompt."""
    if contains_sensitive_leak(text):
        return SECURITY_REFUSAL_MESSAGE, True
    return text, False
