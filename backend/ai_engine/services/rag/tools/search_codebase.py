"""
Cong cu search_codebase dong goi chuan Function Calling cho ReAct Agent (Slide 58 SE373).
Cho phep Agent tu dong tra cuu ma nguon va tai lieu du an khi can thiet.
"""

from typing import Any
from ..schemas import SourceType
from ..config import get_rag_config

SEARCH_CODEBASE_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "search_codebase",
        "description": "Tra cứu mã nguồn, thuật toán, mô hình dữ liệu (Models), API views và tài liệu kiến trúc của dự án Music Tracking.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi hoặc từ khóa kỹ thuật cần tra cứu (ví dụ: 'thuật toán KNN gợi ý', 'cách tính repeat loops', 'cơ chế mã hóa token Fernet').",
                },
                "source_type": {
                    "type": "string",
                    "enum": ["code", "doc", "any"],
                    "description": "Lọc theo loại tài nguyên: 'code' (chỉ mã nguồn Python), 'doc' (chỉ tài liệu Markdown), hoặc 'any' (mặc định tất cả).",
                    "default": "any",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Số lượng đoạn mã liên quan nhất cần lấy về (mặc định 3, tối đa 5).",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}


def search_codebase(query: str, source_type: str = "any", top_k: int = 3) -> str:
    """
    Ham thuc thi cong cu tra cuu codebase cho Agent.
    Tra ve chuoi Markdown chua cac doan code kem duong dan va toa do dong.
    """
    from ..service import get_rag_service

    service = get_rag_service()
    filters = None
    if source_type in [SourceType.CODE.value, SourceType.DOC.value]:
        filters = {"source_type": source_type}

    safe_k = min(max(int(top_k), 1), 5)
    hits = service.cascade.run(query=query, final_k=safe_k, filters=filters)

    if not hits:
        return "Không tìm thấy đoạn mã nguồn hoặc tài liệu nào liên quan đến truy vấn."

    output_blocks = []
    for i, hit in enumerate(hits, start=1):
        meta = hit.chunk.metadata
        symbol_info = f" | Symbol: `{meta.symbol}`" if meta.symbol else ""
        header = f"### [{i}] {meta.path} (Dòng {meta.line_start}-{meta.line_end}){symbol_info}"
        code_block = f"```python\n{hit.chunk.text}\n```"
        output_blocks.append(f"{header}\n{code_block}")

    return "\n\n".join(output_blocks)
