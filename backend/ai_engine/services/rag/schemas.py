"""
Dinh nghia Schemas Pydantic v2 cho He thong RAG Codebase.
Tuan thu Metadata Schema chuan cho Codebase (Slide 18 SE373).
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Phan loai nguon tai lieu."""
    CODE = "code"
    DOC = "doc"
    ANY = "any"


class ChunkMetadata(BaseModel):
    """Metadata gan kem moi phan doan chunk."""
    doc_id: str = Field(description="Ma bam SHA-1 12 ky tu cua duong dan file")
    chunk_id: str = Field(description="Dinh danh tat dinh doc_id:index")
    path: str = Field(description="Duong dan tuong doi tu goc workspace")
    source_type: str = Field(default=SourceType.CODE.value)
    symbol: str | None = Field(default=None, description="Ten Class.Method hoac Function")
    line_start: int = Field(default=1, description="Dong bat dau (1-indexed)")
    line_end: int = Field(default=1, description="Dong ket thuc (1-indexed)")
    heading_path: str | None = Field(default=None, description="Phan cap tieu de Markdown")
    status: str = Field(default="active", description="Trang thai hieu luc")
    app_name: str | None = Field(default=None, description="Ten Django App")

    def to_dict(self) -> dict[str, Any]:
        """Chuyen sang dictionary voi gia tri phu hop cho ChromaDB."""
        return {
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "path": self.path,
            "source_type": self.source_type,
            "symbol": self.symbol or "",
            "line_start": self.line_start,
            "line_end": self.line_end,
            "heading_path": self.heading_path or "",
            "status": self.status,
            "app_name": self.app_name or "",
        }


class CodeChunk(BaseModel):
    """Dai dien cho 1 phan doan noi dung kem metadata."""
    text: str = Field(description="Noi dung ma nguon hoac doan van ban")
    metadata: ChunkMetadata

    def to_chroma_format(self) -> tuple[str, dict[str, Any], str]:
        """Xuat dinh dang nạp vao ChromaDB: (document, metadata, id)."""
        return (self.text, self.metadata.to_dict(), self.metadata.chunk_id)


class SearchHit(BaseModel):
    """Ket qua truy xuat tu Vector Store hoac BM25 Store."""
    chunk: CodeChunk
    dense_score: float | None = None
    sparse_score: float | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None


class CitationItem(BaseModel):
    """Trich dan nguon da duoc kiem chung."""
    citation_id: str = Field(description="Nhan trich dan vi du S1, S2")
    file_path: str = Field(description="Duong dan file vat ly")
    line_start: int
    line_end: int
    symbol: str | None = None
    snippet: str = Field(description="Doan code hoac text trich dan")


class RAGQueryResponse(BaseModel):
    """Hop dong du lieu tra ve cho Client hoac Agent."""
    query: str
    answer: str
    citations: list[CitationItem] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    retrieved_chunks_count: int = 0
