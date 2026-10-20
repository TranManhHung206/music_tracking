"""
Syntax-Aware Python Chunker su dung Abstract Syntax Tree (AST).
Boc tach ma nguon theo ranh gioi Class, Method va Function, bao toan decorators va context.
"""

import ast
import hashlib
from pathlib import Path
from ..schemas import ChunkMetadata, CodeChunk, SourceType


class PythonASTChunker:
    """Phan doan file Python dua tren AST nham bao toan cau truc ngu nghia."""

    def __init__(self, min_lines: int = 3, max_chars: int = 2500):
        self.min_lines = min_lines
        self.max_chars = max_chars

    def chunk_file(self, file_path: Path, relative_path: str, app_name: str | None = None) -> list[CodeChunk]:
        """Doc va phan doan file Python theo AST."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return []

        return self.chunk_code(content, relative_path=relative_path, app_name=app_name)

    def chunk_code(self, code_str: str, relative_path: str, app_name: str | None = None) -> list[CodeChunk]:
        """Phan doan chuoi ma nguon Python."""
        lines = code_str.splitlines(keepends=True)
        if not lines:
            return []

        doc_id = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]

        try:
            tree = ast.parse(code_str)
        except SyntaxError:
            # Fallback cat theo dong neu AST loi cu phap
            return self._fallback_line_chunk(lines, doc_id, relative_path, app_name)

        chunks: list[CodeChunk] = []
        chunk_idx = 0

        # Trích xuất module docstring và phần mở đầu nếu có
        module_doc = ast.get_docstring(tree)
        if module_doc:
            doc_lines = module_doc.strip().splitlines()
            start_l = 1
            end_l = min(len(doc_lines) + 2, len(lines))
            chunk_text = "".join(lines[start_l - 1:end_l]).strip()
            if len(chunk_text) >= 20:
                meta = ChunkMetadata(
                    doc_id=doc_id,
                    chunk_id=f"{doc_id}:{chunk_idx}",
                    path=relative_path,
                    source_type=SourceType.CODE.value,
                    symbol=f"{Path(relative_path).stem}.__doc__",
                    line_start=start_l,
                    line_end=end_l,
                    app_name=app_name,
                )
                chunks.append(CodeChunk(text=chunk_text, metadata=meta))
                chunk_idx += 1

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chunk = self._create_function_chunk(node, lines, doc_id, chunk_idx, relative_path, app_name)
                if chunk:
                    chunks.append(chunk)
                    chunk_idx += 1

            elif isinstance(node, ast.ClassDef):
                class_chunks = self._create_class_chunks(node, lines, doc_id, chunk_idx, relative_path, app_name)
                for chunk in class_chunks:
                    chunks.append(chunk)
                    chunk_idx += 1

        if not chunks:
            return self._fallback_line_chunk(lines, doc_id, relative_path, app_name)

        return chunks

    def _get_node_start_line(self, node: ast.AST) -> int:
        """Lay dong bat dau bao gom ca decorators neu co."""
        if hasattr(node, "decorator_list") and node.decorator_list:
            return node.decorator_list[0].lineno
        return getattr(node, "lineno", 1)

    def _create_function_chunk(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        lines: list[str],
        doc_id: str,
        chunk_idx: int,
        relative_path: str,
        app_name: str | None,
        prefix_class: str | None = None,
    ) -> CodeChunk | None:
        """Tao chunk cho mot ham hoac phuong thuc."""
        start_line = self._get_node_start_line(node)
        end_line = getattr(node, "end_lineno", len(lines))
        func_text = "".join(lines[start_line - 1:end_line]).strip()

        if not func_text:
            return None

        symbol = f"{prefix_class}.{node.name}" if prefix_class else node.name

        # Neu la phuong thuc trong class, bo sung class signature context
        if prefix_class:
            context_header = f"# Ngữ cảnh: Lớp {prefix_class}\n"
            text_with_context = context_header + func_text
        else:
            text_with_context = func_text

        meta = ChunkMetadata(
            doc_id=doc_id,
            chunk_id=f"{doc_id}:{chunk_idx}",
            path=relative_path,
            source_type=SourceType.CODE.value,
            symbol=symbol,
            line_start=start_line,
            line_end=end_line,
            app_name=app_name,
        )
        return CodeChunk(text=text_with_context, metadata=meta)

    def _create_class_chunks(
        self,
        node: ast.ClassDef,
        lines: list[str],
        doc_id: str,
        start_idx: int,
        relative_path: str,
        app_name: str | None,
    ) -> list[CodeChunk]:
        """Tao chunks cho mot class (tach class header va tung method neu class dai)."""
        start_line = self._get_node_start_line(node)
        end_line = getattr(node, "end_lineno", len(lines))
        total_lines = end_line - start_line + 1

        # Neu class ngan (< 40 dong), giu nguyen ca class
        if total_lines <= 40:
            class_text = "".join(lines[start_line - 1:end_line]).strip()
            meta = ChunkMetadata(
                doc_id=doc_id,
                chunk_id=f"{doc_id}:{start_idx}",
                path=relative_path,
                source_type=SourceType.CODE.value,
                symbol=node.name,
                line_start=start_line,
                line_end=end_line,
                app_name=app_name,
            )
            return [CodeChunk(text=class_text, metadata=meta)]

        # Neu class dai, trich xuat class header va cac phuong thuc
        chunks: list[CodeChunk] = []
        curr_idx = start_idx

        # Chunk 1: Class header + docstring + class attributes
        header_end = start_line + 15
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                header_end = self._get_node_start_line(item) - 1
                break
        header_end = max(start_line, min(header_end, end_line))
        header_text = "".join(lines[start_line - 1:header_end]).strip()

        if header_text:
            meta = ChunkMetadata(
                doc_id=doc_id,
                chunk_id=f"{doc_id}:{curr_idx}",
                path=relative_path,
                source_type=SourceType.CODE.value,
                symbol=f"{node.name}.__header__",
                line_start=start_line,
                line_end=header_end,
                app_name=app_name,
            )
            chunks.append(CodeChunk(text=header_text, metadata=meta))
            curr_idx += 1

        # Cac chunks con lai la tung phuong thuc cua class
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                m_chunk = self._create_function_chunk(
                    item, lines, doc_id, curr_idx, relative_path, app_name, prefix_class=node.name
                )
                if m_chunk:
                    chunks.append(m_chunk)
                    curr_idx += 1

        return chunks

    def _fallback_line_chunk(
        self, lines: list[str], doc_id: str, relative_path: str, app_name: str | None
    ) -> list[CodeChunk]:
        """Fallback phan doan theo dong khi file khong dung cu phap AST."""
        chunks = []
        step = 50
        overlap = 10
        total = len(lines)
        idx = 0

        for start in range(0, total, step - overlap):
            end = min(start + step, total)
            text = "".join(lines[start:end]).strip()
            if text:
                meta = ChunkMetadata(
                    doc_id=doc_id,
                    chunk_id=f"{doc_id}:{idx}",
                    path=relative_path,
                    source_type=SourceType.CODE.value,
                    symbol=f"{Path(relative_path).stem}:L{start+1}-L{end}",
                    line_start=start + 1,
                    line_end=end,
                    app_name=app_name,
                )
                chunks.append(CodeChunk(text=text, metadata=meta))
                idx += 1
            if end >= total:
                break

        return chunks
