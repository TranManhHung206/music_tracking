"""
AI Persona Inference Service
Phan tich tam ly va ca tinh am nhac da nha cung cap:
1. Uu tien: Groq API voi model openai/gpt-oss-120b (toc do cao, JSON structured output).
2. Du phong: Google Gemini API (gemini-2.0-flash hoac gemini-1.5-flash).
3. Fallback Heuristic: Sinh bao cao tam ly dua tren Audio Features thuc te neu khong co API key.
"""

import json
import logging
from django.conf import settings
from django.utils import timezone

from analytics.services.filters import get_time_range_bounds
from analytics.services.calculations import (
    get_top_artists,
    get_radar_features,
    get_listening_heatmap,
)
from ai_engine.models import AIMusicPersona

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Bạn là Aura - Chuyên gia Phân tích Tâm lý & Giám tuyển Âm nhạc chuyên nghiệp.
Nhiệm vụ của bạn là phân tích thói quen nghe nhạc, các chỉ số Audio Features và khung giờ nghe của người dùng để đưa ra nhận xét sâu sắc, hóm hỉnh và truyền cảm hứng về cá tính cũng như tâm trạng hiện tại của họ.

Bạn BẮT BUỘC phải trả về định dạng Strict JSON (không dùng Markdown code block ```json), với cấu trúc chính xác sau:
{
  "persona_title": "Tiêu đề cá tính âm nhạc (ví dụ: The Late-Night Sonic Rebel)",
  "tagline": "Khẩu hiệu ngắn gọn đúc kết phong cách (1 câu)",
  "vibe_summary": "Phân tích tâm lý và thói quen nghe nhạc chi tiết từ 2-3 câu bằng tiếng Việt có dấu.",
  "mood_distribution": {
    "energetic": <tính toán số nguyên % dựa trên energy và nhịp điệu bài hát>,
    "melancholic": <tính toán số nguyên % dựa trên valence thấp và các bài acoustic/trầm>,
    "focused": <tính toán số nguyên % còn lại để tổng bằng 100>
  },
  "recommended_listening_time": "Khung giờ nghe lý tưởng (ví dụ: 21:00 - 23:00)",
  "ai_advice": "Lời khuyên âm nhạc dành riêng cho họ (1-2 câu tiếng Việt)."
}
Lưu ý quan trọng: Tuyệt đối không dùng số cố định mẫu. Hãy phân bổ 3 tỷ lệ phần trăm trong mood_distribution linh hoạt theo đúng chỉ số audio features và các nghệ sĩ thực tế của người dùng sao cho tổng đúng 100.
"""

def extract_user_music_context(user, period_type: str = 'monthly') -> dict:
    """Tong hop ngu canh thong ke am nhac cua nguoi dung tu module analytics."""
    range_mapping = {
        'weekly': '7d',
        'monthly': '30d',
        'all_time': '1y',
    }
    time_range = range_mapping.get(period_type, '30d')
    start_dt, end_dt, _ = get_time_range_bounds(time_range)

    # 1. Top artists
    top_artists_data = get_top_artists(user, start_dt, end_dt, limit=5)
    top_artist_names = [a['name'] for a in top_artists_data] or ["Nghệ sĩ đa dạng"]

    # 2. Audio features summary
    radar_data = get_radar_features(user, start_dt, end_dt, time_range)
    features_map = {item['attribute']: item['score'] for item in radar_data.get('features', [])}

    # 3. Peak listening hours tu Heatmap
    heatmap_data = get_listening_heatmap(user, start_dt, end_dt, time_range)
    matrix = heatmap_data.get('matrix', [])
    peak_cells = sorted(matrix, key=lambda c: c.get('count', 0), reverse=True)[:3]
    peak_hours = [f"{c['hour']:02d}:00 - {c['hour']+1:02d}:00" for c in peak_cells if c.get('count', 0) > 0]
    if not peak_hours:
        peak_hours = ["20:00 - 22:00"]

    return {
        "user_name": user.get_full_name() or user.username,
        "period": f"Kỳ {period_type}",
        "top_artists": top_artist_names,
        "peak_listening_hours": peak_hours,
        "audio_features_summary": {
            "valence": features_map.get('valence', 0.5),
            "energy": features_map.get('energy', 0.5),
            "danceability": features_map.get('danceability', 0.5),
            "acousticness": features_map.get('acousticness', 0.5),
            "tempo_normalized": features_map.get('tempo_normalized', 0.5),
        }
    }

def call_groq_inference(context_dict: dict) -> tuple[dict, str]:
    """Goi Groq API voi model openai/gpt-oss-120b tra ve JSON structured output."""
    groq_api_key = getattr(settings, 'GROQ_API_KEY', '') or ''
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY khong duoc thiet lap.")

    model_name = getattr(settings, 'AI_MODEL_GROQ', 'openai/gpt-oss-120b')
    from groq import Groq
    client = Groq(api_key=groq_api_key)

    user_prompt = f"Dữ liệu phân tích người dùng:\n{json.dumps(context_dict, ensure_ascii=False, indent=2)}"

    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        model=model_name,
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    response_text = chat_completion.choices[0].message.content
    parsed_json = json.loads(response_text)
    return parsed_json, f"groq:{model_name}"

def call_gemini_inference(context_dict: dict) -> tuple[dict, str]:
    """Goi Google Gemini API lam kenh du phong fallback."""
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY khong duoc thiet lap.")

    from google import genai
    client = genai.Client(api_key=gemini_key)
    user_prompt = f"{SYSTEM_PROMPT}\n\nDữ liệu phân tích người dùng:\n{json.dumps(context_dict, ensure_ascii=False, indent=2)}"

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_prompt,
        config={"response_mime_type": "application/json"}
    )
    parsed_json = json.loads(response.text)
    return parsed_json, "gemini:gemini-2.0-flash"

def generate_heuristic_persona(context_dict: dict) -> tuple[dict, str]:
    """Sinh bao cao persona dua tren thuat toan tam ly hoc thuc nghiem neu chua co API key."""
    features = context_dict.get('audio_features_summary', {})
    val = features.get('valence', 0.5)
    ene = features.get('energy', 0.5)
    aco = features.get('acousticness', 0.5)
    dan = features.get('danceability', 0.5)
    artists_str = ", ".join(context_dict.get('top_artists', [])[:3])
    peak_str = context_dict.get('peak_listening_hours', ["21:00 - 23:00"])[0]

    if ene >= 0.65 and val <= 0.45:
        title = "The Late-Night Sonic Rebel"
        tagline = "Đêm khuya, năng lượng bùng nổ và chiều sâu nội tâm đa tầng."
        vibe = (
            f"Bạn có xu hướng đắm mình trong âm nhạc vào khung giờ {peak_str}. "
            f"Gu nghe nhạc đồng hành cùng các giai điệu giàu năng lượng từ {artists_str}, "
            "nhưng ẩn sâu bên trong là những khoảng lặng suy tư đầy cuốn hút."
        )
        moods = {"energetic": 45, "melancholic": 35, "focused": 20}
        advice = "Hãy bổ sung vài bản acoustic nhẹ nhàng vào cuối tuần để thư giãn hệ thần kinh."
    elif ene >= 0.60 and dan >= 0.60:
        title = "The Kinetic Dynamo"
        tagline = "Nhịp điệu sôi động, chuyển động không ngừng và lan tỏa năng lượng."
        vibe = (
            f"Âm nhạc của bạn là nguồn nhiên liệu thúc đẩy sự hứng khởi với các nghệ sĩ như {artists_str}. "
            f"Khung giờ nghe đỉnh điểm {peak_str} cho thấy bạn luôn giữ nhịp sống sôi nổi và tích cực."
        )
        moods = {"energetic": 55, "euphoric": 30, "focused": 15}
        advice = "Duy trì năng lượng tích cực này cùng các playlist Upbeat khi làm việc!"
    elif aco >= 0.55:
        title = "The Acoustic Wanderer"
        tagline = "Mộc mạc, yên bình và tìm kiếm sự tĩnh tại trong từng nốt nhạc."
        vibe = (
            f"Bạn yêu thích không gian mộc mạc và chân thực, thường lắng nghe {artists_str}. "
            "Giai điệu acoustic giúp bạn lắng đọng tâm trí và kết nối sâu sắc với cảm xúc nội tại."
        )
        moods = {"peaceful": 50, "melancholic": 30, "reflective": 20}
        advice = "Một tách trà ấm cùng giai điệu Indie Folk sẽ là người bạn đồng hành hoàn hảo cho bạn."
    else:
        title = "The Eclectic Explorer"
        tagline = "Linh hoạt, rộng mở và sẵn sàng chu du qua mọi sắc thái âm nhạc."
        vibe = (
            f"Thư viện âm nhạc của bạn hội tụ sự phong phú từ {artists_str}. "
            f"Bạn đón nhận giai điệu ở khung giờ {peak_str} một cách tự nhiên và cởi mở."
        )
        moods = {"balanced": 40, "curious": 35, "relaxed": 25}
        advice = "Tiếp tục khám phá các thể loại âm nhạc mới để làm giàu thêm thế giới quan của mình."

    result = {
        "persona_title": title,
        "tagline": tagline,
        "vibe_summary": vibe,
        "mood_distribution": moods,
        "recommended_listening_time": peak_str,
        "ai_advice": advice,
    }
    return result, "heuristic:rule-engine"

def generate_and_save_persona(user, period_type: str = 'monthly') -> AIMusicPersona:
    """Tong hop ngu canh, goi AI Engine da tang va luu vao co so du lieu."""
    context_dict = extract_user_music_context(user, period_type)
    persona_data = None
    provider_info = "unknown"

    # 1. Thu nghiem Groq API
    try:
        persona_data, provider_info = call_groq_inference(context_dict)
        logger.info(f"Groq Persona generated successfully for user {user.username}")
    except Exception as e_groq:
        logger.warning(f"Groq Persona inference failed: {e_groq}. Trying Gemini fallback...")
        # 2. Thu nghiem Gemini API
        try:
            persona_data, provider_info = call_gemini_inference(context_dict)
            logger.info(f"Gemini Persona generated successfully for user {user.username}")
        except Exception as e_gem:
            logger.warning(f"Gemini Persona inference failed: {e_gem}. Falling back to Heuristic Engine.")
            # 3. Fallback Heuristic
            persona_data, provider_info = generate_heuristic_persona(context_dict)

    # Chuan hoa tong mood_distribution dung 100% neu AI tra ve le
    moods = persona_data.get('mood_distribution', {})
    if isinstance(moods, dict) and moods:
        total_m = sum(moods.values())
        if total_m != 100 and total_m > 0:
            first_k = next(iter(moods))
            moods[first_k] += (100 - total_m)
    else:
        moods = {"energetic": 40, "focused": 30, "melancholic": 30}

    provider_name, model_used = provider_info.split(':', 1) if ':' in provider_info else (provider_info, 'default')

    # Luu vao Database
    persona_obj = AIMusicPersona.objects.create(
        user=user,
        period_type=period_type,
        persona_title=persona_data.get('persona_title', 'Music Explorer'),
        tagline=persona_data.get('tagline', 'Âm nhạc là phản chiếu của tâm hồn.'),
        vibe_summary=persona_data.get('vibe_summary', ''),
        mood_distribution=moods,
        recommended_listening_time=persona_data.get('recommended_listening_time', '20:00 - 22:00'),
        ai_advice=persona_data.get('ai_advice', ''),
        provider_used=provider_name,
        model_name=model_used,
        raw_ai_response=persona_data,
    )

    return persona_obj
