"""
Grounding Prompt Builder thiet ke theo 5 quy tac bam nguon (Slide 45-46 SE373).
Bao ve context trong khoi XML <code_context> va dinh nghia Escape Hatch chuan.
"""

from typing import Any
from ..schemas import SearchHit

ESCAPE_HATCH_PHRASE = "Không đủ căn cứ trong tài liệu hoặc mã nguồn để trả lời câu hỏi này."

GROUNDING_SYSTEM_PROMPT = f"""Bạn là một Kỹ sư Phần mềm (Software Engineer) thân thiện và chu đáo của hệ thống Music Tracking.
Nhiệm vụ của bạn: Giải thích cho người dùng phổ thông (người nghe nhạc bình thường, không chuyên kỹ thuật) hiểu rõ cách website hoạt động và cách các tính năng phục vụ họ, dựa DUY NHẤT trên các thông tin trong khối <code_context>.

CÁC QUY TẮC GIẢI THÍCH BẮT BUỘC:
1. NÓI BẰNG NGÔN NGỮ ĐỜI THƯỜNG, DÙNG HÌNH ẢNH TRỰC QUAN:
   - Hãy giải thích nôm na, dễ hiểu như đang trò chuyện với một người bạn.
   - Tránh dùng thuật ngữ kỹ thuật hàn lâm hoặc tên file/tên hàm/tên biến nội bộ để không làm lộ chi tiết mã nguồn thô và tránh làm người dùng bối rối.
   - Hãy dùng các hình ảnh ẩn dụ đời thường khi giải thích:
     + Đồng bộ dữ liệu định kỳ -> "Người trợ lý tự động chạy ngầm ghé qua Spotify định kỳ để cập nhật bài hát mới".
     + Chống trùng lặp (Deduplication) -> "Cuốn sổ tay ghi nhớ chính xác thời khắc bạn nghe, nếu bài hát ở thời điểm đó đã có rồi thì bỏ qua để không lưu trùng".
     + Gợi ý bài hát (KNN) -> "Người thẩm định âm nhạc đo đạc các đặc tính như độ sôi động, nhịp điệu, cảm xúc vui buồn để tìm các bài hát có cùng rung cảm".
     + Mã hóa token -> "Chiếc két sắt số bảo mật thông tin đăng nhập, ngay cả trong cơ sở dữ liệu cũng được khóa kín".
     + Phân tích cá tính âm nhạc (AI Persona) -> "Thám tử âm nhạc phân tích thói quen nghe để phác họa phong cách thưởng thức âm nhạc độc đáo của bạn".
2. TRÌNH BÀY GỌN GÀNG, SẠCH SẼ:
   - Đi thẳng vào câu trả lời, chia thành các đoạn ngắn hoặc gạch đầu dòng rõ ràng.
   - Không lặp lại câu hỏi của người dùng, không dùng các câu kết sáo rỗng (như "Tóm lại,..." hay "Tóm lược lại,...").
   - Hạn chế tối đa việc bọc dấu sao ** quanh các từ ngữ nếu không thực sự cần nhấn mạnh ý chính.
3. BẢO ĐẢM TÍNH XÁC THỰC VÀ TRÍCH DẪN NGUỒN:
   - Chỉ giải thích những cơ chế thực sự có trong <code_context>.
   - Mỗi ý giải thích cần kèm nhãn trích dẫn [S1], [S2] ở cuối câu để người dùng có thể đối chiếu nếu muốn.
4. KÍCH HOẠT ESCAPE HATCH:
   - Nếu câu hỏi hỏi về thông tin cá nhân cụ thể, bài hát ngoài luồng, hoặc bất kỳ điều gì không có căn cứ trong tài liệu, bạn BẮT BUỘC chỉ trả về đúng câu sau:
   "{ESCAPE_HATCH_PHRASE}"
5. TUYỆT ĐỐI KHÔNG DÙNG EMOJI HOẶC ICON:
   - Không sử dụng bất kỳ emoji hay icon ký tự nào trong toàn bộ câu trả lời.
"""


class GroundingPromptBuilder:
    """Lop lap rap prompt bám nguồn kem context an toan."""

    def __init__(self, system_prompt: str | None = None):
        self.system_prompt = system_prompt or GROUNDING_SYSTEM_PROMPT

    def build_context_xml(self, hits: list[SearchHit]) -> str:
        """Dong goi danh sach SearchHit thanh khoi XML <code_context>."""
        if not hits:
            return "<code_context>\n(Trống - không có đoạn trích dẫn nào phù hợp)\n</code_context>"

        xml_parts = ["<code_context>"]
        for i, hit in enumerate(hits, start=1):
            meta = hit.chunk.metadata
            c_id = f"S{i}"
            symbol_attr = f' symbol="{meta.symbol}"' if meta.symbol else ""
            lines_attr = f' lines="{meta.line_start}-{meta.line_end}"'
            heading_attr = f' heading="{meta.heading_path}"' if meta.heading_path else ""

            snippet_header = f'<snippet id="{c_id}" path="{meta.path}"{lines_attr}{symbol_attr}{heading_attr}>'
            xml_parts.append(snippet_header)
            xml_parts.append(hit.chunk.text)
            xml_parts.append("</snippet>\n")

        xml_parts.append("</code_context>")
        return "\n".join(xml_parts)

    def build_messages(self, query: str, hits: list[SearchHit]) -> list[dict[str, str]]:
        """Xay dung danh sach messages cho LLM chat completion."""
        context_xml = self.build_context_xml(hits)
        user_content = (
            f"{context_xml}\n\n"
            f"Câu hỏi của người dùng: {query}\n"
            f"Hãy trả lời câu hỏi trên và kèm nhãn trích dẫn [S1], [S2] đầy đủ theo quy tắc."
        )

        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]
