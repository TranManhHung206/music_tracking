"""
Pipeline dieu phoi quet va phan doan toan bo Codebase va Tai lieu.
"""

import os
from pathlib import Path
from ..schemas import CodeChunk
from .python_chunker import PythonASTChunker
from .doc_chunker import MarkdownDocChunker
from ..config import get_rag_config

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".venv",
    "venv",
    "migrations",
    ".git",
    "node_modules",
    "dist",
    "build",
    "chroma_db",
    "data",
    "owner_md",
    ".agents",
}

EXCLUDED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".sqlite3",
    ".log",
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".pkl",
}


class IngestionPipeline:
    """Dieu phoi quet thu muc, chon chunker phu hop va tra ve danh sach chunks."""

    def __init__(self, workspace_root: Path | None = None):
        config = get_rag_config()
        self.workspace_root = workspace_root or config.workspace_root
        self.py_chunker = PythonASTChunker()
        self.doc_chunker = MarkdownDocChunker()

    def run(self) -> list[CodeChunk]:
        """Thuc thi quet toan bo codebase va tra ve danh sach chunks."""
        all_chunks: list[CodeChunk] = []

        # 1. Quet Backend Python files
        backend_dir = self.workspace_root / "backend"
        if backend_dir.exists():
            for root, dirs, files in os.walk(backend_dir):
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES]
                for file_name in files:
                    file_path = Path(root) / file_name
                    if file_path.suffix == ".py":
                        rel_path = file_path.relative_to(self.workspace_root).as_posix()
                        app_name = self._detect_app_name(rel_path)
                        chunks = self.py_chunker.chunk_file(file_path, rel_path, app_name)
                        all_chunks.extend(chunks)

        # 2. Quet duy nhat tai lieu cong khai chinh thuc: README.md
        readme_path = self.workspace_root / "README.md"
        if readme_path.exists():
            rel_path = readme_path.relative_to(self.workspace_root).as_posix()
            chunks = self.doc_chunker.chunk_file(readme_path, rel_path)
            all_chunks.extend(chunks)

        return all_chunks

    def chunk_single_file(self, file_path: Path) -> list[CodeChunk]:
        """Phan doan mot file don le."""
        if not file_path.exists():
            return []

        rel_path = file_path.relative_to(self.workspace_root).as_posix()
        for excluded in EXCLUDED_DIR_NAMES:
            if f"/{excluded}/" in f"/{rel_path}/" or rel_path.startswith(f"{excluded}/"):
                return []

        suffix = file_path.suffix.lower()

        if suffix == ".py":
            app_name = self._detect_app_name(rel_path)
            return self.py_chunker.chunk_file(file_path, rel_path, app_name)
        elif suffix in [".md", ".markdown"]:
            return self.doc_chunker.chunk_file(file_path, rel_path)

        return []

    def _detect_app_name(self, rel_path: str) -> str | None:
        """Trich xuat ten Django app tu duong dan tuong doi."""
        parts = rel_path.split("/")
        if len(parts) >= 2 and parts[0] == "backend":
            return parts[1]
        return None
