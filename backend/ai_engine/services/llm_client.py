"""
OpenAI-Compatible LLM Client & Provider Routing Helper.
Chuan hoa ket noi den cac endpoint chuan OpenAI /v1/chat/completions
(DeepSeek, Ollama, vLLM, Proxy...) bang httpx co san trong .venv.
"""

from dataclasses import dataclass, field
import json
import logging
import os
import re
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_OPENAI_COMPATIBLE_ALIASES = {
    "openai_compatible",
    "openai-compatible",
    "openai",
    "custom",
    "deepseek",
    "local",
}
_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass(frozen=True)
class OpenAICompatibleConfig:
    base_url: str
    api_key: str
    model: str
    model_backup: str = ""
    timeout_seconds: float = 45.0

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url.strip() and self.model.strip())

    @property
    def model_candidates(self) -> list[str]:
        models: list[str] = []
        if self.model.strip():
            models.append(self.model.strip())
        backup = self.model_backup.strip()
        if backup and backup not in models:
            models.append(backup)
        return models


@dataclass
class NormalizedFunctionCall:
    name: str
    arguments: str


@dataclass
class NormalizedToolCall:
    id: str
    function: NormalizedFunctionCall
    type: str = "function"


@dataclass
class NormalizedMessage:
    role: str = "assistant"
    content: str | None = ""
    tool_calls: list[NormalizedToolCall] = field(default_factory=list)


def normalize_openai_chat_completions_url(raw_base_url: str) -> str:
    """Chuan hoa DNS / Base URL thanh endpoint .../chat/completions."""
    cleaned = (raw_base_url or "").strip().rstrip("/")
    if not cleaned:
        return ""

    if not re.match(r"^https?://", cleaned, re.IGNORECASE):
        host_part = cleaned.split("/", 1)[0].lower()
        is_local = (
            host_part.startswith("localhost")
            or host_part.startswith("127.0.0.1")
            or host_part.startswith("0.0.0.0")
            or host_part.startswith("[::1]")
        )
        scheme = "http" if is_local else "https"
        cleaned = f"{scheme}://{cleaned}"

    parsed = urlsplit(cleaned)
    path = (parsed.path or "").rstrip("/")
    if path.endswith("/chat/completions"):
        final_path = path
    elif not path:
        final_path = "/v1/chat/completions"
    else:
        final_path = f"{path}/chat/completions"

    return urlunsplit((parsed.scheme, parsed.netloc, final_path, "", ""))


def get_openai_compatible_config() -> OpenAICompatibleConfig:
    """Doc cau hinh OpenAI-compatible tu Django settings va bien moi truong."""
    base_url = (
        getattr(settings, "LLM_BASE_URL", "")
        or os.getenv("LLM_BASE_URL", "")
        or os.getenv("OPENAI_BASE_URL", "")
    )
    api_key = (
        getattr(settings, "LLM_API_KEY", "")
        or os.getenv("LLM_API_KEY", "")
        or os.getenv("OPENAI_API_KEY", "")
    )
    model = (
        getattr(settings, "LLM_MODEL", "")
        or os.getenv("LLM_MODEL", "")
        or os.getenv("AI_MODEL_CUSTOM", "")
    )
    model_backup = (
        getattr(settings, "LLM_MODEL_BACKUP", "")
        or os.getenv("LLM_MODEL_BACKUP", "")
    )
    try:
        timeout = max(5.0, float(getattr(settings, "LLM_TIMEOUT_SECONDS", 45.0) or 45.0))
    except (TypeError, ValueError):
        timeout = 45.0

    return OpenAICompatibleConfig(
        base_url=str(base_url).strip(),
        api_key=str(api_key).strip(),
        model=str(model).strip(),
        model_backup=str(model_backup).strip(),
        timeout_seconds=timeout,
    )


def get_ai_provider_order() -> list[str]:
    """Xac dinh thu tu uu tien goi nha cung cap LLM theo AI_PROVIDER."""
    raw_provider = (
        getattr(settings, "AI_PROVIDER", "")
        or os.getenv("AI_PROVIDER", "groq")
    )
    provider = str(raw_provider).strip().lower()

    if provider in _OPENAI_COMPATIBLE_ALIASES:
        return ["openai_compatible", "groq", "gemini"]
    if provider == "gemini":
        return ["gemini", "openai_compatible", "groq"]
    return ["groq", "openai_compatible", "gemini"]


def strip_reasoning_blocks(text: str) -> str:
    """Loai bo khoi <think>...</think> neu model suy luan tra ve trong content."""
    if not text:
        return ""
    cleaned = _THINK_BLOCK_RE.sub("", str(text))
    return cleaned.strip()


def extract_json_object(raw_text: str) -> dict[str, Any]:
    """Phan tich JSON an toan ke ca khi model kem <think> hoac markdown fence."""
    cleaned = strip_reasoning_blocks(raw_text)
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
        cleaned = _CODE_FENCE_RE.sub("", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx > start_idx:
        candidate = cleaned[start_idx : end_idx + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Khong the tach JSON hop le tu phan hoi LLM.")


def _serialize_message(msg: Any) -> dict[str, Any]:
    """Chuyen message dict hoac object SDK sang payload JSON chuan OpenAI."""
    if isinstance(msg, dict):
        return msg

    role = getattr(msg, "role", "assistant") or "assistant"
    content = getattr(msg, "content", "")
    payload: dict[str, Any] = {"role": role, "content": content if content is not None else ""}

    raw_tool_calls = getattr(msg, "tool_calls", None) or []
    if raw_tool_calls:
        serialized_calls = []
        for idx, tc in enumerate(raw_tool_calls):
            fn = getattr(tc, "function", None)
            fn_name = getattr(fn, "name", "") if fn else ""
            fn_args = getattr(fn, "arguments", "{}") if fn else "{}"
            if isinstance(fn_args, dict):
                fn_args = json.dumps(fn_args, ensure_ascii=False)
            serialized_calls.append(
                {
                    "id": getattr(tc, "id", None) or f"call_{idx}",
                    "type": getattr(tc, "type", "function") or "function",
                    "function": {
                        "name": str(fn_name),
                        "arguments": str(fn_args),
                    },
                }
            )
        payload["tool_calls"] = serialized_calls
    return payload


def _parse_tool_calls(raw_calls: Any) -> list[NormalizedToolCall]:
    if not isinstance(raw_calls, list):
        return []
    parsed: list[NormalizedToolCall] = []
    for idx, item in enumerate(raw_calls):
        if not isinstance(item, dict):
            continue
        fn_raw = item.get("function") if isinstance(item.get("function"), dict) else {}
        fn_name = str(fn_raw.get("name") or "")
        raw_args = fn_raw.get("arguments")
        if isinstance(raw_args, dict):
            fn_args = json.dumps(raw_args, ensure_ascii=False)
        elif raw_args is None:
            fn_args = "{}"
        else:
            fn_args = str(raw_args)
        parsed.append(
            NormalizedToolCall(
                id=str(item.get("id") or f"call_{idx}"),
                function=NormalizedFunctionCall(name=fn_name, arguments=fn_args),
                type=str(item.get("type") or "function"),
            )
        )
    return parsed


class _ChatCompletionsAdapter:
    """Cung cap giao dien .chat.completions.create() tuong thich ReAct Agent va chat."""

    def __init__(self, owner: "OpenAICompatibleClient"):
        self._owner = owner

    def create(
        self,
        *,
        model: str,
        messages: list[Any],
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
    ) -> SimpleNamespace:
        msg = self._owner.create_chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            tools=tools,
            tool_choice=tool_choice,
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class OpenAICompatibleClient:
    """HTTP client goi cac endpoint chuan OpenAI Chat Completions qua httpx."""

    def __init__(self, config: OpenAICompatibleConfig | None = None):
        self.config = config or get_openai_compatible_config()
        self.endpoint_url = normalize_openai_chat_completions_url(self.config.base_url)
        self.chat = SimpleNamespace(completions=_ChatCompletionsAdapter(self))

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _post_payload(self, payload: dict[str, Any]) -> httpx.Response:
        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            return client.post(
                self.endpoint_url,
                headers=self._build_headers(),
                json=payload,
            )

    def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[Any],
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
    ) -> NormalizedMessage:
        if not self.endpoint_url:
            raise ValueError("LLM_BASE_URL chua duoc thiet lap.")

        payload: dict[str, Any] = {
            "model": model,
            "messages": [_serialize_message(m) for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        resp = self._post_payload(payload)

        # Mot so endpoint OpenAI-compatible hoac DeepSeek proxy khong ho tro response_format
        if resp.status_code == 400 and "response_format" in payload:
            fallback_payload = dict(payload)
            fallback_payload.pop("response_format", None)
            resp = self._post_payload(fallback_payload)

        if resp.status_code == 429:
            raise RuntimeError(f"HTTP 429 rate_limit tu endpoint cho model {model}")

        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI-compatible endpoint loi HTTP {resp.status_code} cho model {model}")

        data = resp.json()
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise RuntimeError("Phan hoi OpenAI-compatible thieu truong choices.")

        raw_msg = choices[0].get("message") or {}
        content = raw_msg.get("content")
        if content is None:
            content = ""
        return NormalizedMessage(
            role=str(raw_msg.get("role") or "assistant"),
            content=str(content) if not isinstance(content, str) else content,
            tool_calls=_parse_tool_calls(raw_msg.get("tool_calls")),
        )
