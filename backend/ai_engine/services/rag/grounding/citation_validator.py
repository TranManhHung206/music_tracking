"""
Citation Validator tu dong kiem chung nguon goc trich dan tren he thong file vat ly (Slide 47-48 SE373).
Kiem tra File Existence, Line Range va do luong chi so Citation Existence Rate & Citation Accuracy.
"""

import re
from pathlib import Path
from ..schemas import SearchHit, CitationItem
from ..config import get_rag_config
from .prompt_builder import ESCAPE_HATCH_PHRASE


class CitationValidator:
    """Kiem dinh trich dan nguon [S1], [S2] tu cau tra loi cua LLM."""

    def __init__(self, workspace_root: Path | None = None):
        config = get_rag_config()
        self.workspace_root = workspace_root or config.workspace_root
        self.citation_regex = re.compile(r"\[(S\d+)\]")

    def validate(
        self, answer: str, hits: list[SearchHit]
    ) -> tuple[list[CitationItem], dict]:
        """
        Kiem tra tinh hop le cua toan bo nhan trich dan trong cau tra loi.
        Tra ve (danh sach CitationItem hop le, dictionary metrics kiem dinh).
        """
        # Truong hop model tra ve Escape Hatch hop le
        if ESCAPE_HATCH_PHRASE.lower() in answer.lower():
            return [], {
                "is_escape_hatch": True,
                "total_citations": 0,
                "citation_existence_rate": 1.0,
                "citation_accuracy": 1.0,
                "all_valid": True,
            }

        # Tim tat ca cac nhan trich dan dang [S1], [S2]
        cited_labels = self.citation_regex.findall(answer)
        unique_labels = list(dict.fromkeys(cited_labels))

        if not unique_labels:
            # Khong co trich dan
            return [], {
                "is_escape_hatch": False,
                "total_citations": 0,
                "citation_existence_rate": 1.0,
                "citation_accuracy": 1.0,
                "all_valid": True,
            }

        valid_citations: list[CitationItem] = []
        valid_context_count = 0
        valid_file_count = 0

        # Tao lookup map S1 -> SearchHit
        hit_map: dict[str, SearchHit] = {
            f"S{i}": hit for i, hit in enumerate(hits, start=1)
        }

        for label in unique_labels:
            if label not in hit_map:
                # LLM tu bia ra nhan trich dan khong co trong context (Failure Mode 4)
                continue

            valid_context_count += 1
            hit = hit_map[label]
            meta = hit.chunk.metadata

            # Kiem tra su ton tai cua file vat ly tren dia
            full_path = self.workspace_root / meta.path
            file_exists = full_path.exists() and full_path.is_file()
            line_valid = False

            if file_exists:
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_lines_count = sum(1 for _ in f)
                    if 1 <= meta.line_start <= meta.line_end <= max(file_lines_count, 1):
                        line_valid = True
                except Exception:
                    line_valid = False

            if file_exists and line_valid:
                valid_file_count += 1

            # Tao snippet ngan gon
            snippet_text = hit.chunk.text.strip()
            if len(snippet_text) > 200:
                snippet_text = snippet_text[:200] + "..."

            valid_citations.append(
                CitationItem(
                    citation_id=label,
                    file_path=meta.path,
                    line_start=meta.line_start,
                    line_end=meta.line_end,
                    symbol=meta.symbol,
                    snippet=snippet_text,
                )
            )

        total_cited = len(unique_labels)
        citation_existence_rate = (
            round(valid_context_count / total_cited, 4) if total_cited > 0 else 1.0
        )
        citation_accuracy = (
            round(valid_file_count / total_cited, 4) if total_cited > 0 else 1.0
        )
        all_valid = (citation_existence_rate == 1.0 and citation_accuracy == 1.0)

        metrics = {
            "is_escape_hatch": False,
            "total_citations": total_cited,
            "valid_context_citations": valid_context_count,
            "valid_file_citations": valid_file_count,
            "citation_existence_rate": citation_existence_rate,
            "citation_accuracy": citation_accuracy,
            "all_valid": all_valid,
        }

        return valid_citations, metrics
