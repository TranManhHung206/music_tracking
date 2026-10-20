"""
Cau hinh he thong RAG Codebase.
Quan ly hang so thuat toan RRF k=60, nguong phan doan va duong dan thu muc.
"""

from pathlib import Path
from pydantic import BaseModel, Field

# Xac dinh thu muc goc cua workspace
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parents[3]
WORKSPACE_ROOT = CURRENT_FILE.parents[4]
DATA_DIR = BACKEND_DIR / "ai_engine" / "data"


class RAGConfig(BaseModel):
    """Lop cau hinh tap trung cho he thong RAG."""

    workspace_root: Path = Field(default=WORKSPACE_ROOT)
    data_dir: Path = Field(default=DATA_DIR)
    chroma_persist_dir: Path = Field(default=DATA_DIR / "chroma_db")
    bm25_persist_path: Path = Field(default=DATA_DIR / "bm25_index.pkl")
    collection_name: str = Field(default="music_tracking_codebase")

    # Hang so thuat toan RRF (Slide 35 SE373)
    rrf_k: int = Field(default=60)

    # Cac nguong Thac truy xuat (Retrieval Cascade - Slide 40)
    overfetch_top_k: int = Field(default=50)
    rrf_top_k: int = Field(default=20)
    final_top_k: int = Field(default=5)

    # Cau hinh phan doan (Chunking)
    min_chunk_lines: int = Field(default=3)
    max_chunk_chars: int = Field(default=2500)
    chunk_overlap_chars: int = Field(default=200)

    # Cache TTL cho Redis (giay)
    cache_ttl_seconds: int = Field(default=3600)

    class Config:
        arbitrary_types_allowed = True


_config_instance: RAGConfig | None = None


def get_rag_config() -> RAGConfig:
    """Tra ve singleton cau hinh RAG."""
    global _config_instance
    if _config_instance is None:
        _config_instance = RAGConfig()
        _config_instance.data_dir.mkdir(parents=True, exist_ok=True)
        _config_instance.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    return _config_instance
