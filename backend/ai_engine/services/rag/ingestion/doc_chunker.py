"""
Markdown & Document Chunker phan doan theo tieu de phan cap (Heading-Aware).
Bao toan khoi ma nguon (code blocks) va ghi nhan heading_path.
"""

import re
import hashlib
from pathlib import Path
from ..schemas import ChunkMetadata, CodeChunk, SourceType


class MarkdownDocChunker:
    """Phan doan tai lieu Markdown dua tren tieu de phan cap."""

    def __init__(self, max_chars: int = 2500):
        self.max_chars = max_chars

    def chunk_file(self, file_path: Path, relative_path: str) -> list[CodeChunk]:
        """Doc va phan doan file Markdown."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return []
        return self.chunk_text(content, relative_path)

    def chunk_text(self, text: str, relative_path: str) -> list[CodeChunk]:
        """Phan doan chuoi Markdown."""
        lines = text.splitlines(keepends=True)
        if not lines:
            return []

        doc_id = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]
        chunks: list[CodeChunk] = []

        # Tách các section theo heading
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
        sections: list[dict] = []
        current_heading_stack: list[str] = []
        current_lines: list[str] = []
        start_line = 1
        in_code_block = False

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block

            match = heading_pattern.match(stripped) if not in_code_block else None

            if match:
                # Kết thúc section trước nếu có nội dung
                if current_lines:
                    sections.append({
                        "heading_path": " > ".join(current_heading_stack) if current_heading_stack else "Introduction",
                        "lines": current_lines,
                        "line_start": start_line,
                        "line_end": i - 1,
                    })
                    current_lines = []

                level = len(match.group(1))
                title = match.group(2).strip()

                # Cập nhật ngăn xếp tiêu đề
                while len(current_heading_stack) >= level:
                    current_heading_stack.pop()
                current_heading_stack.append(title)
                start_line = i

            current_lines.append(line)

        # Lưu section cuối
        if current_lines:
            sections.append({
                "heading_path": " > ".join(current_heading_stack) if current_heading_stack else "Document",
                "lines": current_lines,
                "line_start": start_line,
                "line_end": len(lines),
            })

        # Chuyển các section thành CodeChunk
        chunk_idx = 0
        for sec in sections:
            sec_text = "".join(sec["lines"]).strip()
            if len(sec_text) < 20:
                continue

            # Nếu section quá dài, chia nhỏ theo đoạn văn
            if len(sec_text) > self.max_chars:
                sub_chunks = self._split_long_section(sec, doc_id, chunk_idx, relative_path)
                chunks.extend(sub_chunks)
                chunk_idx += len(sub_chunks)
            else:
                meta = ChunkMetadata(
                    doc_id=doc_id,
                    chunk_id=f"{doc_id}:{chunk_idx}",
                    path=relative_path,
                    source_type=SourceType.DOC.value,
                    symbol=sec["heading_path"].split(" > ")[-1],
                    line_start=sec["line_start"],
                    line_end=sec["line_end"],
                    heading_path=sec["heading_path"],
                )
                chunks.append(CodeChunk(text=sec_text, metadata=meta))
                chunk_idx += 1

        return chunks

    def _split_long_section(
        self, sec: dict, doc_id: str, start_idx: int, relative_path: str
    ) -> list[CodeChunk]:
        """Chia nho section dai theo khoi doan van."""
        sub_chunks: list[CodeChunk] = []
        lines = sec["lines"]
        curr_lines: list[str] = []
        curr_start = sec["line_start"]
        idx = start_idx

        for offset, line in enumerate(lines):
            curr_lines.append(line)
            current_len = sum(len(l) for l in curr_lines)

            if current_len >= self.max_chars and not line.strip().startswith("```"):
                text = "".join(curr_lines).strip()
                if text:
                    sub_end = curr_start + len(curr_lines) - 1
                    meta = ChunkMetadata(
                        doc_id=doc_id,
                        chunk_id=f"{doc_id}:{idx}",
                        path=relative_path,
                        source_type=SourceType.DOC.value,
                        symbol=sec["heading_path"].split(" > ")[-1],
                        line_start=curr_start,
                        line_end=sub_end,
                        heading_path=sec["heading_path"],
                    )
                    sub_chunks.append(CodeChunk(text=text, metadata=meta))
                    idx += 1
                curr_start = curr_start + len(curr_lines)
                curr_lines = []

        if curr_lines:
            text = "".join(curr_lines).strip()
            if text:
                sub_end = sec["line_end"]
                meta = ChunkMetadata(
                    doc_id=doc_id,
                    chunk_id=f"{doc_id}:{idx}",
                    path=relative_path,
                    source_type=SourceType.DOC.value,
                    symbol=sec["heading_path"].split(" > ")[-1],
                    line_start=curr_start,
                    line_end=sub_end,
                    heading_path=sec["heading_path"],
                )
                sub_chunks.append(CodeChunk(text=text, metadata=meta))

        return sub_chunks
