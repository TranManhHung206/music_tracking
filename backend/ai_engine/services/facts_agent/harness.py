"""
Agent Harness Module - Bo khung dieu khien & Bao ve an toan (Agent = Model + Harness).
Thuc thi cac Code Guardrails:
1. Tool Whitelist & Sandbox Execution.
2. Verification Gate & Output Sanitization (Kiem tra format JSON, triet tieu emoji).
3. Fallback Heuristic Engine dua tren cac tools DB thuc te khi khong co Groq API key hoac gap loi 429.
"""

import re
import random
import logging
from typing import Any
from tracker.models import ListeningHistory
from .tools import (
    query_repeat_loops,
    query_night_owl_anomaly,
    query_marathon_sessions,
    query_artist_dominance,
    query_tempo_or_energy_contrast,
)
from ..rag.tools.search_codebase import search_codebase, SEARCH_CODEBASE_TOOL_SPEC

logger = logging.getLogger(__name__)

# Danh sach cac cong cu duoc phep thuc thi (Whitelist)
ALLOWED_TOOLS = {
    'query_repeat_loops': query_repeat_loops,
    'query_night_owl_anomaly': query_night_owl_anomaly,
    'query_marathon_sessions': query_marathon_sessions,
    'query_artist_dominance': query_artist_dominance,
    'query_tempo_or_energy_contrast': query_tempo_or_energy_contrast,
    'search_codebase': search_codebase,
}

# OpenAI Spec Tool Definitions cho Groq Function Calling
GROQ_TOOL_DEFINITIONS = [
    SEARCH_CODEBASE_TOOL_SPEC,
    {
        "type": "function",
        "function": {
            "name": "query_repeat_loops",
            "description": "Tìm kiếm các bài hát được người dùng nghe lặp lại nhiều lần trong cùng một ngày (Repeat Loops).",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_repeats": {
                        "type": "integer",
                        "description": "Số lượt nghe tối thiểu trong một ngày (mặc định 3).",
                        "default": 3,
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_night_owl_anomaly",
            "description": "Điều tra thói quen nghe nhạc đêm khuya (00:00 - 05:00 sáng), đo lường tỷ lệ nghe ban đêm và các nghệ sĩ được nghe nhiều nhất lúc khuya.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_marathon_sessions",
            "description": "Truy vết phiên nghe nhạc liên tục dài nhất (Marathon Listening Session), thời lượng số giờ và số bài hát đã nghe.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_artist_dominance",
            "description": "Đo lường mức độ trung thành với nghệ sĩ đứng đầu và tỷ lệ phần trăm chiếm sóng thư viện trong kỳ.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_tempo_or_energy_contrast",
            "description": "Kiểm tra sự thay đổi cảm xúc hoặc nhịp điệu đột ngột giữa hai bài hát nghe liền kề nhau (ví dụ: chuyển từ ballad sang EDM).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

def execute_agent_tool(tool_name: str, tool_args: dict, user, start_dt, end_dt) -> dict:
    """
    Rao chan bao ve: Chi thuc thi cac tool nam trong ALLOWED_TOOLS.
    Bat moi ngoai le va tra ve ket qua an toan cho LLM.
    """
    if tool_name not in ALLOWED_TOOLS:
        return {"error": f"Tool '{tool_name}' khong nam trong danh sach cho phep."}

    func = ALLOWED_TOOLS[tool_name]
    try:
        if tool_name == 'query_repeat_loops':
            min_r = tool_args.get('min_repeats', 3)
            return func(user, start_dt, end_dt, min_repeats=min_r)
        elif tool_name == 'search_codebase':
            query = tool_args.get('query', '')
            source_type = tool_args.get('source_type', 'any')
            top_k = tool_args.get('top_k', 3)
            return {"result": func(query=query, source_type=source_type, top_k=top_k)}
        else:
            return func(user, start_dt, end_dt)
    except Exception as e:
        logger.error(f"Loi khi thuc thi tool {tool_name}: {e}")
        return {"error": f"Loi khi truy van: {str(e)}"}

def sanitize_and_verify_facts(facts_list: list) -> list[dict]:
    """
    Verification Gate: Kiem tra va lam sach du lieu Facts truoc khi tra ve cho Client.
    Bao dam tinh toan ven, loai bo emoji, gan ID mac dinh neu thieu.
    Tu dong chuyen doi ngoi xung ho thanh 'ban' va loai bo fact phu dinh 0%.
    """
    valid_facts = []
    category_choices = [
        'repeat_loop', 'night_owl', 'marathon',
        'artist_dominance', 'contrast', 'milestone', 'general'
    ]

    negative_keywords = ['không nghe bất kỳ', 'không phát', 'bằng 0%', 'tỷ lệ nghe ban đêm bằng 0%']

    for idx, item in enumerate(facts_list):
        if not isinstance(item, dict):
            continue

        cat = item.get('category', 'general')
        if cat not in category_choices:
            cat = 'general'

        raw_desc = str(item.get('description') or "").strip()
        metric_hl = str(item.get('metric_highlight') or "").strip()

        # Loai bo cac fact mang tinh phu dinh hoac 0% khong co gia tri insight
        if metric_hl in ['0%', '0', '0 lượt']:
            continue
        if any(kw in raw_desc.lower() for kw in negative_keywords):
            continue

        # Chuyen doi xung ho khach sao thanh 'ban'
        clean_desc = re.sub(r'\bngười dùng\b', 'bạn', raw_desc, flags=re.IGNORECASE)
        clean_desc = re.sub(r'\bthính giả\b', 'bạn', clean_desc, flags=re.IGNORECASE)

        fact_dict = {
            "id": str(item.get('id') or f"fact-{idx+1}"),
            "category": cat,
            "badge": str(item.get('badge') or "Sự Thật Âm Nhạc").strip(),
            "title": str(item.get('title') or "Thói quen nghe nhạc").strip(),
            "description": clean_desc,
            "metric_highlight": metric_hl,
            "evidence": str(item.get('evidence') or "").strip(),
        }

        # Loc bo emoji hoac ky tu khong mong muon theo Rule 2.2
        fact_dict["badge"] = fact_dict["badge"].encode('ascii', 'ignore').decode('ascii') if not any(ord(c) > 127 for c in fact_dict["badge"]) else fact_dict["badge"]
        valid_facts.append(fact_dict)

    return valid_facts

def generate_heuristic_facts(user, start_dt, end_dt) -> list[dict]:
    """
    Heuristic Fallback Engine:
    Tu dong goi cac tools truc tiep tren co so du lieu va tong hop dung 3 facts thuc te
    xung ho 'ban' than thiet, khong bao gio co fact phu dinh.
    """
    facts = []

    # 1. Kiem tra Repeat Loops
    repeat_data = query_repeat_loops(user, start_dt, end_dt, min_repeats=3)
    if repeat_data.get("has_data") and repeat_data.get("top_repeats"):
        top_rep = repeat_data["top_repeats"][0]
        facts.append({
            "id": "fact-repeat-loop",
            "category": "repeat_loop",
            "badge": "Vòng Lặp Vô Tận",
            "title": f"Cơn Nghiện {top_rep['track_name']}",
            "description": (
                f"Bạn đã bấm nghe đi nghe lại bài hát này {top_rep['repeat_count']} lần "
                f"chỉ trong một ngày ({top_rep['play_date']})."
            ),
            "metric_highlight": f"{top_rep['repeat_count']} lần / ngày",
            "evidence": f"{top_rep['track_name']} - {top_rep['artist_name']} ({top_rep['play_date']})",
        })

    # 2. Kiem tra Artist Dominance
    artist_data = query_artist_dominance(user, start_dt, end_dt)
    if artist_data.get("has_data") and artist_data.get("is_highly_loyal"):
        facts.append({
            "id": "fact-artist-loyalty",
            "category": "artist_dominance",
            "badge": "Độ Trung Thành Tuyệt Đối",
            "title": f"Vùng An Toàn Cùng {artist_data['top_artist_name']}",
            "description": (
                f"Bạn đã dành trọn {artist_data['dominance_percentage']}% toàn bộ "
                f"thời lượng nghe nhạc của mình cho {artist_data['top_artist_name']}."
            ),
            "metric_highlight": f"{artist_data['dominance_percentage']}% thời lượng",
            "evidence": f"{artist_data['top_artist_name']} ({artist_data['top_artist_plays']} lượt)",
        })

    # 3. Kiem tra Marathon Session
    marathon_data = query_marathon_sessions(user, start_dt, end_dt)
    if marathon_data.get("has_data"):
        facts.append({
            "id": "fact-marathon",
            "category": "marathon",
            "badge": "Kỷ Lục Marathon",
            "title": "Phiên Nghe Nhạc Bất Tận",
            "description": (
                f"Bạn đã nghe liên tục {marathon_data['max_tracks_count']} bài hát "
                f"trong suốt {marathon_data['duration_hours']} giờ không ngừng nghỉ."
            ),
            "metric_highlight": f"{marathon_data['duration_hours']} giờ liên tục",
            "evidence": f"Ngày {marathon_data['session_date']} ({marathon_data['time_window']})",
        })

    # 4. Kiem tra Cu Dem (Chi lay khi that su co nghe dem)
    night_data = query_night_owl_anomaly(user, start_dt, end_dt)
    if night_data.get("is_significant_night_owl") and night_data.get("night_plays_count", 0) > 0:
        artist_str = ", ".join(night_data.get("top_night_artists", [])[:2]) or "các bài hát yêu thích"
        facts.append({
            "id": "fact-night-owl",
            "category": "night_owl",
            "badge": "Cú Đêm Năng Lượng",
            "title": "Tâm Hồn Âm Nhạc Về Đêm",
            "description": (
                f"Có tới {night_data['night_percentage']}% tổng số lượt nghe của bạn diễn ra "
                f"vào khung giờ từ 00:00 đến 05:00 sáng cùng {artist_str}."
            ),
            "metric_highlight": f"{night_data['night_percentage']}% lúc đêm khuya",
            "evidence": f"{night_data['night_plays_count']} lượt nghe lúc 00:00 - 05:00",
        })

    # 5. Kiem tra Tuong phan cam xuc (Contrast)
    contrast_data = query_tempo_or_energy_contrast(user, start_dt, end_dt)
    if contrast_data.get("has_data"):
        facts.append({
            "id": "fact-contrast",
            "category": "contrast",
            "badge": "Tắc Kè Hoa Cảm Xúc",
            "title": "Cú Nhảy Năng Lượng Bất Ngờ",
            "description": (
                f"Bạn đã chuyển đổi trạng thái nghe nhạc với độ chênh lệch năng lượng lên tới {contrast_data['energy_contrast']}% "
                f"giữa hai bài hát kế tiếp nhau."
            ),
            "metric_highlight": f"Chênh lệch {contrast_data['energy_contrast']}% năng lượng",
            "evidence": f"{contrast_data['track_before']} sang {contrast_data['track_after']}",
        })

    # 6. Neu van chua du 3 facts, bo sung fact tong the ve tong luot nghe hoac thu vien
    total = ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt)).count()
    if len(facts) < 3:
        facts.append({
            "id": "fact-listening-volume",
            "category": "milestone",
            "badge": "Nhịp Sống Âm Nhạc",
            "title": "Nguồn Cảm Hứng Không Ngừng",
            "description": f"Bạn đã thưởng thức tổng cộng {total} lượt nghe trong kỳ này, giữ vững tình yêu sâu sắc với âm nhạc mỗi ngày.",
            "metric_highlight": f"{total} lượt nghe",
            "evidence": f"Ghi nhận trong {total} lần phát bài hát",
        })

    # Neu co nhieu hon 3 facts hop le, boc ngau nhien 3 facts de tao su da dang phong phu
    if len(facts) > 3:
        return random.sample(facts, 3)

    return facts[:3]

