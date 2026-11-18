"""
Schemas du lieu chuan hoa cho Hybrid Music & Website Assistant.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field

AssistantModeLiteral = Literal["auto", "music_insights", "website_support"]
ResolvedDomainLiteral = Literal["music_insights", "website_support", "clarification"]


class AssistantScopeMeta(BaseModel):
    """Mo ta pham vi thoi gian hoac nguon du lieu duoc dung de tra loi."""

    label: str
    start_date: str | None = None
    end_date: str | None = None
    source: Literal[
        "dashboard_period",
        "requested_in_query",
        "rolling_window",
        "website_docs",
        "clarification",
    ]
    note: str = ""


class AssistantEvidenceItem(BaseModel):
    """Tung bang chung so lieu hoac chi so dinh kem trong cau tra loi."""

    label: str
    value: str
    detail: str = ""
    is_estimate: bool = False
    category: Literal["observed", "calculated", "estimate", "ai_interpretation"] = "observed"


class AssistantTopicItem(BaseModel):
    """Chu de tai lieu than thien danh cho nguoi dung pho thong (an file path noi bo)."""

    id: str
    title: str
    category: str


class AssistantClarificationOption(BaseModel):
    """Lua chon lam ro y dinh khi cau hoi o che do Auto bi mo ho."""

    mode: Literal["music_insights", "website_support"]
    label: str
    query: str


class AssistantResponseMeta(BaseModel):
    """Thong tin van hanh va chinh sach luu tru phien."""

    provider_used: str
    model_name: str
    is_fallback: bool = False
    tools_used: list[str] = Field(default_factory=list)
    session_turns: int = 0
    memory_policy: str = (
        "Lưu tối đa 6 lượt gần nhất mỗi miền trong phiên hiện tại (tối đa 30 phút), "
        "tách biệt dữ liệu âm nhạc và tài liệu website, có thể xóa ngay bất kỳ lúc nào."
    )


class AssistantQueryResult(BaseModel):
    """Hop dong dau ra thong nhat cho endpoint POST /api/ai/assistant/query/."""

    query: str
    answer: str
    active_mode: AssistantModeLiteral
    resolved_domain: ResolvedDomainLiteral
    needs_clarification: bool = False
    clarification_options: list[AssistantClarificationOption] = Field(default_factory=list)
    scope: AssistantScopeMeta
    evidence: list[AssistantEvidenceItem] = Field(default_factory=list)
    topics: list[AssistantTopicItem] = Field(default_factory=list)
    dev_citations: list[dict[str, Any]] = Field(default_factory=list)
    dev_verification: dict[str, Any] | None = None
    dev_metrics: dict[str, Any] | None = None
    meta: AssistantResponseMeta
