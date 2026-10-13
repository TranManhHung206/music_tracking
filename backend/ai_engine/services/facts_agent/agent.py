"""
Aura Music Detective Agent (Model + Harness).
Dieu phoi chu trinh ReAct Tool Calling giua Groq LLM va cac Tools truy van DB.
Kiem soat chat che bang Harness Guardrails: Loop Budget, Tool Whitelist va Verification Gate.
"""

import json
import logging
from django.conf import settings
from .harness import (
    GROQ_TOOL_DEFINITIONS,
    execute_agent_tool,
    sanitize_and_verify_facts,
    generate_heuristic_facts,
)

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """
Bạn là Aura - Music Detective Agent, thám tử âm nhạc đồng hành cá nhân của người dùng.
Nhiệm vụ của bạn: Sử dụng các công cụ được cung cấp để điều tra lịch sử nghe nhạc thực tế, từ đó phát hiện CHÍNH XÁC 3 sự thật âm nhạc (Music Fun Facts) độc đáo, tích cực, hóm hỉnh và cá nhân hóa sâu sắc nhất.

Các quy tắc bắt buộc nghiêm ngặt:
1. XƯNG HÔ THÂN THIỆN: Tuyệt đối CẤM dùng từ "người dùng", "thính giả" hoặc "họ". Bạn BẮT BUỘC phải xưng hô trực tiếp là "bạn" (ví dụ: "Bạn đã cày liên tục...", "Bạn dành trọn 80% thời gian cho...", "Gu nghe nhạc của bạn..."). Hãy trò chuyện thân mật, truyền cảm hứng như người bạn thân âm nhạc (Spotify Wrapped).
2. SỐ LƯỢNG: Bạn BẮT BUỘC phải trả về đúng 3 sự thật âm nhạc khác nhau (3 facts). Hãy gọi từ 2 đến 3 công cụ khác nhau để thu thập đủ dữ liệu đa dạng.
3. CHỈ CHỌN HÀNH VI TÍCH CỰC & NỔI BẬT: Mọi sự thật bạn đưa ra BẮT BUỘC phải dựa trên hành vi nghe thực tế đã diễn ra. Tuyệt đối KHÔNG tạo các sự thật phủ định vô nghĩa (như "bạn không nghe bài nào lúc 3h sáng", "tỷ lệ 0%", "không phát bài nào"). Nếu một công cụ trả về 0 hoặc không có điểm nhấn, hãy chuyển sang gọi công cụ khác.
4. TUYỆT ĐỐI KHÔNG DÙNG EMOJI hoặc icon ký tự nào ở bất kỳ đâu.
5. Khi đã thu thập đủ dữ liệu, hãy trả về kết quả cuối cùng ở định dạng Strict JSON thuần túy (không bọc trong markdown ```json) với cấu trúc:
{
  "facts": [
    {
      "id": "fact-1",
      "category": "repeat_loop" | "night_owl" | "marathon" | "artist_dominance" | "contrast" | "milestone" | "general",
      "badge": "Tên huy hiệu ngắn gọn (ví dụ: Vòng Lặp Vô Tận)",
      "title": "Tiêu đề hấp dẫn ngắn gọn",
      "description": "Nội dung diễn giải chi tiết 1-2 câu xưng hô bạn bè thân thiện",
      "metric_highlight": "Con số điểm nhấn (ví dụ: 18 lần / ngày, 80% thời lượng)",
      "evidence": "Tên bài hát, ca sĩ hoặc mốc thời gian làm bằng chứng"
    }
  ]
}
"""

def run_music_facts_agent(user, start_dt, end_dt, period_label: str = "trong kỳ") -> dict:
    """
    Thuc thi Agentic AI tim kiem Music Fun Facts:
    1. Khoi tao phien hoi thoai voi Groq LLM.
    2. Vong lap ReAct voi Loop Budget toi da 3 iterations.
    3. Thuc thi Tool calls thong qua Harness Sandbox.
    4. Verification Gate kiem tra chat che ket qua dau ra.
    5. Fallback Heuristic Engine tu dong neu gap bat ky su co nao.
    """
    groq_api_key = getattr(settings, 'GROQ_API_KEY', '') or ''
    model_name = getattr(settings, 'AI_MODEL_GROQ', 'openai/gpt-oss-120b')

    # Neu chua cau hinh Groq API key, kich hoat ngay Fallback Heuristic
    if not groq_api_key:
        logger.info("Chua co GROQ_API_KEY, su dung Fallback Heuristic Engine cho Music Facts.")
        facts = generate_heuristic_facts(user, start_dt, end_dt)
        return {
            "facts": facts,
            "agent_meta": {
                "agent_name": "Aura Music Detective",
                "provider_used": "heuristic",
                "model_name": "db-analytics-heuristic",
                "iterations_used": 0,
                "tools_called": ["direct_db_queries"],
                "is_fallback": True,
            }
        }

    from groq import Groq
    client = Groq(api_key=groq_api_key)

    user_name = user.get_full_name() or user.first_name or user.username
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Hãy điều tra lịch sử nghe nhạc của bạn ({user_name}) {period_label} để tìm ra chính xác 3 sự thật âm nhạc nổi bật, tích cực và thú vị nhất.",
        },
    ]

    tools_called = []
    max_iterations = 3
    iterations_used = 0

    try:
        for iteration in range(max_iterations):
            iterations_used += 1

            chat_completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=GROQ_TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.6,
            )

            response_message = chat_completion.choices[0].message
            messages.append(response_message)

            # Kiem tra neu Model yeu cau goi Tool
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    fn_name = tool_call.function.name
                    tools_called.append(fn_name)

                    try:
                        fn_args = json.loads(tool_call.function.arguments or "{}")
                    except Exception:
                        fn_args = {}

                    tool_output = execute_agent_tool(fn_name, fn_args, user, start_dt, end_dt)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": fn_name,
                        "content": json.dumps(tool_output, ensure_ascii=False),
                    })
            else:
                # Model da tong hop xong ket qua cuoi cung
                content = response_message.content or "{}"
                # Loai bo markdown code blocks neu co
                if content.startswith("```"):
                    lines = content.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()

                parsed_data = json.loads(content)
                raw_facts = parsed_data.get("facts", [])
                verified_facts = sanitize_and_verify_facts(raw_facts)

                if verified_facts:
                    # Neu model tra ve it hon 3 facts, bu dap bang heuristic de luon du 3 the
                    if len(verified_facts) < 3:
                        extra_facts = generate_heuristic_facts(user, start_dt, end_dt)
                        existing_cats = {f["category"] for f in verified_facts}
                        for extra in extra_facts:
                            if extra["category"] not in existing_cats and len(verified_facts) < 3:
                                verified_facts.append(extra)
                                existing_cats.add(extra["category"])

                    return {
                        "facts": verified_facts,
                        "agent_meta": {
                            "agent_name": "Aura Music Detective",
                            "provider_used": "groq",
                            "model_name": model_name,
                            "iterations_used": iterations_used,
                            "tools_called": list(set(tools_called)),
                            "is_fallback": False,
                        }
                    }
                break

    except Exception as e:
        logger.warning(f"Su co trong vong lap Groq Agent: {e}. Chuyen doi sang Fallback Heuristic Engine.")

    # Fallback an toan khi gap bat ky loi nao
    fallback_facts = generate_heuristic_facts(user, start_dt, end_dt)
    return {
        "facts": fallback_facts,
        "agent_meta": {
            "agent_name": "Aura Music Detective",
            "provider_used": "heuristic-fallback",
            "model_name": model_name,
            "iterations_used": iterations_used,
            "tools_called": list(set(tools_called)),
            "is_fallback": True,
        }
    }
