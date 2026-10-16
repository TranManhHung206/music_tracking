"""
Aura Music Detective Agent (Model + Harness).
Dieu phoi chu trinh ReAct Tool Calling giua Groq LLM va cac Tools truy van DB.
Kiem soat chat che bang Harness Guardrails: Loop Budget, Tool Whitelist va Verification Gate.
"""

import json
import random
import logging
from django.conf import settings
from django.core.cache import cache
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
3. CHỈ ĐƯỢC GỌI CÔNG CỤ TRONG DANH SÁCH: Tuyệt đối CHỈ ĐƯỢC PHÉP gọi các công cụ đã được cung cấp (query_repeat_loops, query_night_owl_anomaly, query_marathon_sessions, query_artist_dominance, query_tempo_or_energy_contrast). Tuyệt đối CẤM tự ý bịa hoặc gọi các công cụ không có trong danh sách như commentary, thought, analysis.
4. CHỈ CHỌN HÀNH VI TÍCH CỰC & NỔI BẬT: Mọi sự thật bạn đưa ra BẮT BUỘC phải dựa trên hành vi nghe thực tế đã diễn ra. Tuyệt đối KHÔNG tạo các sự thật phủ định vô nghĩa (như "bạn không nghe bài nào lúc 3h sáng", "tỷ lệ 0%", "không phát bài nào"). Nếu một công cụ trả về 0 hoặc không có điểm nhấn, hãy chuyển sang gọi công cụ khác.
5. TUYỆT ĐỐI KHÔNG DÙNG EMOJI hoặc icon ký tự nào ở bất kỳ đâu.
6. Khi đã thu thập đủ dữ liệu, hãy trả về kết quả cuối cùng ở định dạng Strict JSON thuần túy (không bọc trong markdown ```json) với cấu trúc:
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

INVESTIGATION_LEADS = [
    "Hãy đặc biệt chú ý đến thói quen nghe nhạc đêm khuya (cú đêm) và sự thay đổi cảm xúc hoặc nhịp điệu đột ngột giữa các bài hát.",
    "Hãy ưu tiên điều tra mức độ trung thành với nghệ sĩ đứng đầu và các phiên nghe marathon dài bất tận.",
    "Hãy truy vết các bài hát được nghe lặp đi lặp lại nhiều lần trong ngày (repeat loops) và sự tương phản âm thanh thú vị.",
    "Hãy khám phá toàn diện từ các phiên nghe liên tục dài nhất đến thói quen thức khuya nghe nhạc cùng nghệ sĩ yêu thích.",
    "Hãy điều tra sự đối lập về năng lượng và tiết tấu giữa các bài hát liền kề cùng mức độ phủ sóng của top nghệ sĩ.",
]

def is_model_rate_limited(model_name: str) -> bool:
    """Kiem tra xem model co dang bi khoa boi Circuit Breaker do 429 khong."""
    return bool(cache.get(f"groq_circuit_breaker:{model_name}"))

def mark_model_rate_limited(model_name: str, cooldown_seconds: int = 60) -> None:
    """Danh dau model bi khoa tam thoi de chuyen ngay sang tier ke tiep."""
    cache.set(f"groq_circuit_breaker:{model_name}", True, timeout=cooldown_seconds)

def _execute_groq_react_loop(client, model_name: str, user, start_dt, end_dt, period_label: str) -> dict | None:
    """
    Thuc thi 1 luot ReAct Loop tren model Groq cu the.
    Tra ve ket qua dict facts neu thanh cong, hoac None neu that bai / rate limit.
    """
    user_name = user.get_full_name() or user.first_name or user.username
    selected_lead = random.choice(INVESTIGATION_LEADS)
    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Hãy điều tra lịch sử nghe nhạc của bạn ({user_name}) {period_label} "
                f"để tìm ra chính xác 3 sự thật âm nhạc nổi bật, tích cực và thú vị nhất. "
                f"Gợi ý hướng phá án: {selected_lead}"
            ),
        },
    ]

    tools_called = []
    max_iterations = 5
    iterations_used = 0

    # Xao tron ngau nhien thu tu cong cu cho moi phien de LLM khong thien vi cac cong cu dau danh sach
    shuffled_tools = random.sample(GROQ_TOOL_DEFINITIONS, len(GROQ_TOOL_DEFINITIONS))

    try:
        for iteration in range(max_iterations):
            iterations_used += 1

            # Ep model phai tong hop JSON o luot cuoi hoac khi da goi tu 3 cong cu tro len
            force_synthesis = (iteration == max_iterations - 1) or (len(tools_called) >= 3)

            request_params = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.4 if force_synthesis else 0.75,
            }

            if force_synthesis:
                request_params["tools"] = shuffled_tools
                request_params["tool_choice"] = "none"
                request_params["response_format"] = {"type": "json_object"}
            else:
                request_params["tools"] = shuffled_tools
                request_params["tool_choice"] = "auto"

            chat_completion = client.chat.completions.create(**request_params)

            response_message = chat_completion.choices[0].message
            messages.append(response_message)

            if response_message.tool_calls and not force_synthesis:
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
                content = response_message.content or "{}"
                if content.startswith("```"):
                    lines = content.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    content = "\n".join(lines).strip()

                try:
                    parsed_data = json.loads(content)
                    raw_facts = parsed_data.get("facts", [])
                except Exception:
                    raw_facts = []

                verified_facts = sanitize_and_verify_facts(raw_facts)

                if verified_facts:
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
                            "provider_used": f"groq:{model_name}",
                            "model_name": model_name,
                            "iterations_used": iterations_used,
                            "tools_called": list(set(tools_called)),
                            "is_fallback": False,
                        }
                    }
                break

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "rate_limit" in err_msg.lower():
            logger.warning(f"Model {model_name} bi cham nguong Rate Limit (429): {err_msg}. Kich hoat Circuit Breaker 60 giay.")
            mark_model_rate_limited(model_name, cooldown_seconds=60)
        else:
            logger.warning(f"Su co trong ReAct loop cua model {model_name}: {err_msg}")
        return None

    return None

def run_music_facts_agent(user, start_dt, end_dt, period_label: str = "trong kỳ") -> dict:
    """
    Thuc thi Agentic AI tim kiem Music Fun Facts voi kien truc du phong 3 tang:
    1. Tang 1 (Primary): AI_MODEL_GROQ (openai/gpt-oss-120b).
    2. Tang 2 (Backup): AI_MODEL_GROQ_BACKUP (openai/gpt-oss-20b).
    3. Tang 3 (Fallback): Heuristic Engine tinh toan truc tiep tu DB.
    """
    groq_api_key = getattr(settings, 'GROQ_API_KEY', '') or ''
    model_primary = getattr(settings, 'AI_MODEL_GROQ', 'openai/gpt-oss-120b')
    model_backup = getattr(settings, 'AI_MODEL_GROQ_BACKUP', 'openai/gpt-oss-20b')

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

    # 1. Thu nghiem Tang 1: Model Primary (120B)
    if not is_model_rate_limited(model_primary):
        logger.info(f"Khoi chay Tang 1 voi model chinh: {model_primary}")
        result_primary = _execute_groq_react_loop(
            client=client,
            model_name=model_primary,
            user=user,
            start_dt=start_dt,
            end_dt=end_dt,
            period_label=period_label,
        )
        if result_primary:
            return result_primary
    else:
        logger.info(f"Tang 1 ({model_primary}) dang trong Circuit Breaker Cooldown, bo qua.")

    # 2. Thu nghiem Tang 2: Model Backup (20B)
    if not is_model_rate_limited(model_backup):
        logger.info(f"Tang 1 that bai hoac rate limited. Kich hoat Tang 2 du phong: {model_backup}")
        result_backup = _execute_groq_react_loop(
            client=client,
            model_name=model_backup,
            user=user,
            start_dt=start_dt,
            end_dt=end_dt,
            period_label=period_label,
        )
        if result_backup:
            result_backup["agent_meta"]["provider_used"] = f"groq:{model_backup} (backup)"
            return result_backup
    else:
        logger.info(f"Tang 2 ({model_backup}) cung dang trong Circuit Breaker Cooldown, bo qua.")

    # 3. Tang 3: Fallback Heuristic Engine
    logger.warning("Ca 2 tang model Groq deu khong kha dung. Chuyen sang Tang 3: Fallback Heuristic Engine.")
    fallback_facts = generate_heuristic_facts(user, start_dt, end_dt)
    return {
        "facts": fallback_facts,
        "agent_meta": {
            "agent_name": "Aura Music Detective",
            "provider_used": "heuristic-fallback",
            "model_name": "db-analytics-heuristic",
            "iterations_used": 0,
            "tools_called": ["direct_db_queries"],
            "is_fallback": True,
        }
    }
