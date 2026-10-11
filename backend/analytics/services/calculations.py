"""
Analytics Calculations Service
Thuc thi cac truy van tong hop hieu nang cao cap Database bang Django ORM:
Summary, Top Tracks, Top Artists, Audio Features Radar, Listening Heatmap va Bar Chart Race.
"""

from datetime import timedelta
from collections import defaultdict
from django.utils import timezone
from django.db.models import Count, Avg, Sum, F
from django.db.models.functions import ExtractIsoWeekDay, ExtractHour, ExtractYear, ExtractMonth
from tracker.models import ListeningHistory, Track, Artist, Album

DAY_NAMES = {
    1: 'Monday',
    2: 'Tuesday',
    3: 'Wednesday',
    4: 'Thursday',
    5: 'Friday',
    6: 'Saturday',
    7: 'Sunday',
}

def get_listening_summary(user, start_dt, end_dt) -> dict:
    """Tinh toan chi so thong ke tong quan trong ky."""
    qs = ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt))

    stats = qs.aggregate(
        total_plays=Count('id'),
        total_duration_ms=Sum('track__duration_ms'),
    )
    total_plays = stats.get('total_plays') or 0
    total_duration_ms = stats.get('total_duration_ms') or 0
    total_hours = round(total_duration_ms / (1000 * 60 * 60), 2)

    unique_artists_count = qs.values('track__artists').distinct().count()
    unique_albums_count = qs.values('track__album').distinct().count()

    return {
        "total_plays": total_plays,
        "total_duration_ms": total_duration_ms,
        "total_hours": total_hours,
        "unique_artists_count": unique_artists_count,
        "unique_albums_count": unique_albums_count,
    }

def get_top_tracks(user, start_dt, end_dt, limit: int = 10) -> list[dict]:
    """Lay danh sach Top bai hat nghe nhieu nhat trong ky."""
    qs = (
        ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt))
        .values(
            'track__spotify_id',
            'track__name',
            'track__duration_ms',
            'track__album__name',
            'track__album__image_url',
        )
        .annotate(play_count=Count('id'))
        .order_by('-play_count')[:limit]
    )

    results = []
    for item in qs:
        # Lay danh sach nghe si cua track
        track_sp_id = item['track__spotify_id']
        artists = list(
            Artist.objects.filter(tracks__spotify_id=track_sp_id)
            .values_list('name', flat=True)
        )
        results.append({
            "spotify_id": track_sp_id,
            "name": item['track__name'],
            "album_name": item['track__album__name'],
            "album_image_url": item['track__album__image_url'],
            "artists": artists,
            "play_count": item['play_count'],
        })
    return results

def get_top_artists(user, start_dt, end_dt, limit: int = 10) -> list[dict]:
    """Lay danh sach Top nghe si nghe nhieu nhat trong ky."""
    from tracker.models import Album
    qs = (
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
            track__artists__isnull=False
        )
        .values(
            artist_id=F('track__artists__spotify_id'),
            artist_name=F('track__artists__name'),
            image_url=F('track__artists__image_url'),
        )
        .annotate(play_count=Count('id'))
        .order_by('-play_count')[:limit]
    )

    results = []
    for item in qs:
        img_url = item['image_url']
        art_id = item['artist_id']
        # Neu chua co anh nghe si, lay anh album gan nhat cua nghe si do
        if not img_url:
            alb = Album.objects.filter(artists__spotify_id=art_id, image_url__isnull=False).first()
            if alb:
                img_url = alb.image_url
            else:
                trk = Track.objects.filter(artists__spotify_id=art_id, album__image_url__isnull=False).first()
                if trk and trk.album:
                    img_url = trk.album.image_url

        results.append({
            "spotify_id": art_id,
            "name": item['artist_name'],
            "image_url": img_url,
            "play_count": item['play_count'],
        })
    return results

import re

VIETNAMESE_DIACRITICS_REGEX = re.compile(
    r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]',
    re.IGNORECASE
)
CYRILLIC_REGEX = re.compile(r'[\u0400-\u04FF]')

VPOP_ARTISTS = {
    "sivan", "lazii", "thịnh suy", "thinh suy", "dangrangto", "w/n", "changg", "low g",
    "captain boy", "zvc", "267", "antransax", "lynk lee", "hngle", "ari", "donal",
    "fishy", "machiot", "bao han helia", "lemese", "freaky", "tempo g", "titie",
    "nau", "duongg", "nguyenn", "par sg", "xuan dinh k.y", "buitruonglinh", "hyo",
    "pháp kiều", "phap kieu", "coolkid", "danny chung", "codynamvo", "congb",
    "wren evans", "jack", "j97", "jack - j97", "k-icm", "da lab", "chillies",
    "ngọt", "ngot", "cá hồi hoang", "ca hoi hoang", "marzuz", "kai đinh", "kai dinh",
    "lyly", "orange", "amee", "min", "đen", "den", "vũ", "vũ.", "vu", "vũ cát tường",
    "hoàng thùy linh", "grey d", "mono", "soobin", "hieuthuhai", "mck", "tlinh",
    "quang hùng masterd", "quang hung masterd", "tinh hà \"say hi\"", "anh trai say hi",
    "erik", "đức phúc", "duc phuc", "hòa minzy", "hoa minzy", "sơn tùng m-tp", "sơn tùng",
    "son tung", "phương ly", "phuong ly", "hoàng dũng", "hoang dung", "bảo anh",
    "b ray", "karik", "justatee", "bigdaddy", "emily", "tóc tiên", "tiên tiên",
    "phan mạnh quỳnh", "phùng khánh linh", "mr siro", "trịnh thăng bình",
    "hương tràm", "đông nhi", "noo phước thịnh", "trúc nhân", "bùi anh tuấn",
    "trung quân", "thùy chi", "mỹ tâm", "hà anh tuấn", "hà nhi", "tăng duy tân",
    "vương anh tú", "ronboogz", "coldzy", "gill", "tage", "vsoul", "rhyder"
}

VPOP_KEYWORDS = [
    "3 1 0 7", "3107", "10005", "3000km", "good4us", "damsay", "daybyday",
    "ngayquangay", "tinhco", "vanvuong", "say hi", "anh trai", "chị đẹp",
    "rap viet", "chuyện rằng", "lời tạm biệt", "người hay nói"
]

VPOP_EDM_ARTISTS = {
    "hoaprox", "masew", "touliver", "slimv", "triple d", "k-icm"
}

EDM_ARTISTS = {
    "thefatrat", "alan walker", "lost sky", "arc north", "mountkid", "tokyo machine",
    "k-391", "ahrix", "robin hustin", "tobimorrow", "jex", "marshmello", "martin garrix",
    "avicii", "skrillex", "illenium", "ellis", "cadmium", "grant dawson", "raven & kreyn",
    "roy knox", "barren gates", "m.i.m.e", "clarx", "anikdote", "goblins from mars",
    "prismo", "raiko", "danell arma", "uplink", "unknown brain", "i see monstas", "nero",
    "slaydit", "anjulie", "jordan shaw", "tungevaag", "mangoo", "swif7", "temper city"
}

KPOP_ARTISTS = {
    "bts", "blackpink", "newjeans", "twice", "iu", "stray kids", "aespa",
    "jung kook", "jungkook", "jimin", "v", "suga", "rm", "j-hope", "rosé", "rose",
    "lisa", "jennie", "le sserafim", "ive", "seventeen", "exo", "nct", "itzy",
    "txt", "enhypen", "red velvet", "teriyaki boyz"
}

USUK_ARTISTS = {
    "charlie puth", "dua lipa", "the weeknd", "taylor swift", "ariana grande",
    "bruno mars", "billie eilish", "dhruv", "salem ilese", "justin bieber",
    "ed sheeran", "oliver tree", "jvke", "henry moodie", "disco lines", "tinashe",
    "surf mesa", "emilee", "au/ra", "snoop dogg", "tyga", "latto", "tape machines",
    "jowen", "oomiee"
}

import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def load_custom_artist_dataset():
    """Doc tu dong file CSV phan loai nghe si tu backend/analytics/data neu nguoi dung cung cap."""
    if not DATA_DIR.exists():
        return set(), set()

    vn_artists = set()
    foreign_artists = set()

    for csv_file in DATA_DIR.glob("*.csv"):
        try:
            with open(csv_file, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = [h.strip().lower() for h in (reader.fieldnames or [])]

                name_col = next((h for h in headers if h in ["spotify_name", "artist", "artist_name", "name", "nghe_si"]), None)
                type_col = next((h for h in headers if h in ["is_vpop", "type", "country", "region", "is_vietnamese", "quoc_gia", "phan_loai"]), None)

                if not name_col:
                    continue

                for row in reader:
                    row_clean = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items() if k}
                    artist_name = row_clean.get(name_col, "").strip().lower()
                    if not artist_name:
                        continue

                    # Neu cot notes danh dau la 'new' ma chua gan gia tri is_vpop thi bo qua
                    notes_val = row_clean.get("notes", "").lower()

                    if type_col:
                        raw_val = row_clean.get(type_col, "").strip().lower()
                        # Xu ly cac dinh dang 1.0, 1, true, vn
                        if raw_val in ["1", "1.0", "true", "yes", "vn", "vietnam", "viet nam", "vpop", "v-pop", "viet", "trong nuoc"]:
                            vn_artists.add(artist_name)
                        elif raw_val in ["0", "0.0", "false", "no", "foreign", "quoc te", "international", "usuk", "us-uk", "kpop"]:
                            foreign_artists.add(artist_name)
                        elif notes_val != "new" and raw_val:
                            vn_artists.add(artist_name)
                    else:
                        if notes_val != "new":
                            vn_artists.add(artist_name)
        except Exception:
            continue

    return vn_artists, foreign_artists

_CUSTOM_ARTISTS_LOADED = False
_LAST_CSV_MTIME = 0.0

def ensure_custom_artists_loaded():
    """Tu dong kiem tra va nap ngay file CSV khi nguoi dung moi bo file vao ma khong can khoi dong lai server."""
    global _CUSTOM_ARTISTS_LOADED, _LAST_CSV_MTIME
    if not DATA_DIR.exists():
        return
    csv_files = list(DATA_DIR.glob("*.csv"))
    if not csv_files:
        return
    try:
        current_mtime = max(f.stat().st_mtime for f in csv_files)
        if not _CUSTOM_ARTISTS_LOADED or current_mtime != _LAST_CSV_MTIME:
            vn, foreign = load_custom_artist_dataset()
            VPOP_ARTISTS.update(vn)
            USUK_ARTISTS.update(foreign)
            _CUSTOM_ARTISTS_LOADED = True
            _LAST_CSV_MTIME = current_mtime
            try:
                from django.core.cache import cache
                cache.clear()
            except Exception:
                pass
    except Exception:
        pass

ensure_custom_artists_loaded()

def is_artist_match(artist_name_lower: str, target_name: str) -> bool:
    """Kiem tra ten nghe si khop theo tu rieng biet tranh loi substring."""
    pattern = r'\b' + re.escape(target_name.lower()) + r'\b'
    return bool(re.search(pattern, artist_name_lower))

def classify_artist_genres(artist_name: str, track_name: str = "", artists: list = None, track = None) -> str:
    """
    Phan loai the loai am nhac lai (Hybrid Genre Classification) ket hop giua
    sieu du lieu (Metadata: ten nghe si, ngon ngu) va dac trung song am (Audio DSP Features).
    """
    ensure_custom_artists_loaded()
    title = track_name or ""
    title_lower = title.lower()

    if artists:
        artist_names_lower = [a.lower() for a in artists if a]
    elif artist_name:
        artist_names_lower = [artist_name.lower()]
    else:
        artist_names_lower = []

    # Lay cac chi so Audio DSP tu ban ghi Track neu co
    energy = getattr(track, 'energy', 0.0) if track else 0.0
    acousticness = getattr(track, 'acousticness', 0.0) if track else 0.0
    danceability = getattr(track, 'danceability', 0.0) if track else 0.0
    tempo = getattr(track, 'tempo', 0.0) if track else 0.0

    # 1. Kiem tra K-Pop ro rang (vd: Rose co dau sac nhung la K-Pop)
    is_kpop_artist = any(
        any(is_artist_match(a_name, kp) for kp in KPOP_ARTISTS) for a_name in artist_names_lower
    )
    if is_kpop_artist:
        return "K-Pop"

    # 2. Cyrillic (Nga / Dong Au)
    if CYRILLIC_REGEX.search(title) or any(CYRILLIC_REGEX.search(a_name) for a_name in artist_names_lower):
        return "Russian / CIS Pop"

    # 3. Kiem tra nhom am nhac Viet Nam (Metadata)
    has_viet_accent = bool(VIETNAMESE_DIACRITICS_REGEX.search(title)) or any(
        bool(VIETNAMESE_DIACRITICS_REGEX.search(a_name)) for a_name in artist_names_lower
    )
    is_vpop_artist = any(
        any(is_artist_match(a_name, vp) for vp in VPOP_ARTISTS) for a_name in artist_names_lower
    )
    has_vpop_kw = any(kw in title_lower for kw in VPOP_KEYWORDS)
    is_vietnamese = has_viet_accent or is_vpop_artist or has_vpop_kw

    # Kiem tra dau hieu EDM / Electronic chung
    is_edm_artist = any(any(is_artist_match(a_name, ea) for ea in EDM_ARTISTS) for a_name in artist_names_lower)
    is_edm_title = any(k in title_lower for k in ["remix", "radio edit", "dubstep", "bass", "club mix", "prod."])

    if is_vietnamese:
        # Nhom V-Pop phan nhanh chi tiet bang dac trung song am DSP
        is_vpop_edm_artist = any(
            any(is_artist_match(a_name, ea) for ea in VPOP_EDM_ARTISTS) for a_name in artist_names_lower
        )
        is_vpop_remix = (
            any(k in title_lower for k in ["remix", "vinahouse", "dubstep", "club mix"])
            and not any(k in title_lower for k in ["acoustic", "piano", "lofi", "chill"])
        )
        is_vpop_edm_dsp = (energy >= 0.85 and tempo >= 128 and acousticness <= 0.25 and danceability >= 0.65)
        if is_vpop_edm_artist or is_vpop_remix or is_vpop_edm_dsp:
            return "V-Pop (Electronic / Dance)"
        if acousticness >= 0.50 or (energy <= 0.48 and danceability <= 0.55) or any(k in title_lower for k in ["acoustic", "piano", "lofi", "chill"]):
            return "V-Pop (Acoustic / Indie)"
        if danceability >= 0.68 or any(a in ["low g", "pháp kiều", "phap kieu", "hieuthuhai", "wren evans", "binz", "freaky"] for a in artist_names_lower):
            return "V-Pop (R&B / Hip-Hop)"
        return "V-Pop (Modern Pop)"

    # 4. Nhom Quoc te / Au My phan nhanh chi tiet bang dac trung song am DSP
    if is_edm_artist or is_edm_title or (energy >= 0.78 and acousticness <= 0.35):
        return "EDM / Electronic"

    if "montagem" in title_lower or "phonk" in title_lower or (energy >= 0.90 and tempo >= 135):
        return "Phonk / High Energy"

    if acousticness >= 0.60 or (energy <= 0.45 and tempo <= 100) or any(k in title_lower for k in ["acoustic", "piano", "lofi", "chill"]):
        return "Acoustic / Lo-Fi"

    if danceability >= 0.75 or any(a in ["snoop dogg", "a$ap rocky", "eminem", "drake"] for a in artist_names_lower):
        return "Hip-Hop / Rap"

    is_usuk_artist = any(any(is_artist_match(a_name, ua) for ua in USUK_ARTISTS) for a_name in artist_names_lower)
    if is_usuk_artist:
        return "US-UK / Pop"

    return "Global Pop"

def get_genre_distribution(user, start_dt, end_dt) -> dict:
    """Phan tich ti le cac the loai am nhac trong lich su nghe cua nguoi dung."""
    ensure_custom_artists_loaded()
    history = (
        ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt))
        .select_related('track')
        .prefetch_related('track__artists')
    )

    genre_counts = {}
    genre_colors = {
        "V-Pop (Electronic / Dance)": "#A855F7",
        "V-Pop (Acoustic / Indie)": "#10B981",
        "EDM / Electronic": "#1DB954",
        "Acoustic / Lo-Fi": "#14B8A6",
        "Phonk / High Energy": "#E11D48",
        "V-Pop (R&B / Hip-Hop)": "#F59E0B",
        "V-Pop (Modern Pop)": "#EC4899",
        "US-UK / Pop": "#3B82F6",
        "Hip-Hop / Rap": "#F97316",
        "K-Pop": "#FBBF24",
        "Russian / CIS Pop": "#8B5CF6",
        "Global Pop": "#06B6D4",
    }

    total_plays = 0
    for lh in history:
        t = lh.track
        artists = list(t.artists.all()) if t else []
        artist_names = [a.name for a in artists]
        art_name = artist_names[0] if artist_names else ""
        trk_name = t.name if t else ""
        genre = classify_artist_genres(art_name, trk_name, artists=artist_names, track=t)
        genre_counts[genre] = genre_counts.get(genre, 0) + 1
        total_plays += 1

    if total_plays == 0:
        return {"genres": [], "total_plays": 0, "top_genre": "Chưa có dữ liệu"}

    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    genres_list = []
    for g_name, count in sorted_genres:
        pct = round((count / total_plays) * 100, 1)
        genres_list.append({
            "name": g_name,
            "plays": count,
            "percentage": pct,
            "color": genre_colors.get(g_name, "#64748B"),
        })

    return {
        "genres": genres_list,
        "total_plays": total_plays,
        "top_genre": genres_list[0]["name"] if genres_list else "Đa dạng",
    }

def get_radar_features(user, start_dt, end_dt, time_range_label: str = '30d') -> dict:
    """Tinh toan 5 dac tinh am thanh chuan hoa [0.0, 1.0] cho bieu do Radar."""
    qs = ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt))
    total_tracks = qs.count()

    stats = qs.aggregate(
        avg_valence=Avg('track__valence'),
        avg_energy=Avg('track__energy'),
        avg_danceability=Avg('track__danceability'),
        avg_acousticness=Avg('track__acousticness'),
        avg_tempo=Avg('track__tempo'),
    )

    raw_valence = stats.get('avg_valence') or 0.5
    raw_energy = stats.get('avg_energy') or 0.5
    raw_danceability = stats.get('avg_danceability') or 0.5
    raw_acousticness = stats.get('avg_acousticness') or 0.5
    raw_tempo = stats.get('avg_tempo') or 120.0

    # Chuan hoa BPM ve [0.0, 1.0] (tempo chia cho 200)
    norm_tempo = min(max(raw_tempo / 200.0, 0.0), 1.0)

    features = [
        {"attribute": "valence", "score": round(min(max(raw_valence, 0.0), 1.0), 2), "description": "Tích cực, vui tươi"},
        {"attribute": "energy", "score": round(min(max(raw_energy, 0.0), 1.0), 2), "description": "Sôi động, mạnh mẽ"},
        {"attribute": "danceability", "score": round(min(max(raw_danceability, 0.0), 1.0), 2), "description": "Dễ nhảy, nhịp điệu rõ"},
        {"attribute": "acousticness", "score": round(min(max(raw_acousticness, 0.0), 1.0), 2), "description": "Mộc mạc, ít điện tử"},
        {"attribute": "tempo_normalized", "score": round(norm_tempo, 2), "description": "Tốc độ nhịp (BPM chuẩn hóa)"},
    ]

    return {
        "time_range": time_range_label,
        "total_tracks_analyzed": total_tracks,
        "features": features,
    }

def get_listening_heatmap(user, start_dt, end_dt, time_range_label: str = '30d') -> dict:
    """Trích xuất ma trận mật độ nghe nhạc 7 ngày trong tuần x 24 giờ trong ngày."""
    qs = (
        ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt))
        .annotate(
            day_of_week=ExtractIsoWeekDay('played_at'), # 1 (Mon) den 7 (Sun)
            hour=ExtractHour('played_at'),              # 0 den 23
        )
        .values('day_of_week', 'hour')
        .annotate(count=Count('id'))
        .order_by('day_of_week', 'hour')
    )

    matrix_map = {(item['day_of_week'], item['hour']): item['count'] for item in qs}
    matrix = []
    max_density = 0

    # Xay dung luoi 7 x 24 day du
    for day in range(1, 8):
        for h in range(24):
            cnt = matrix_map.get((day, h), 0)
            if cnt > max_density:
                max_density = cnt
            matrix.append({
                "day_of_week": day,
                "day_name": DAY_NAMES.get(day, "Unknown"),
                "hour": h,
                "count": cnt,
            })

    return {
        "time_range": time_range_label,
        "max_density": max_density,
        "matrix": matrix,
    }

def get_bar_chart_race(user, start_dt, end_dt, top_n: int = 5) -> dict:
    """
    Tong hop luot nghe luy ke don dieu theo tung thang cua Top 5 nghe si.
    Dam bao timeline co it nhat 2 moc thoi gian theo chuan verify_analytics_engine.py.
    """
    # 1. Tim Top N nghe si trong toan bo ky
    top_artists_qs = (
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
            track__artists__isnull=False
        )
        .values('track__artists__name')
        .annotate(total=Count('id'))
        .order_by('-total')[:top_n]
    )
    top_artist_names = [a['track__artists__name'] for a in top_artists_qs if a['track__artists__name']]

    # Fallback neu chua co du lieu
    if not top_artist_names:
        top_artist_names = ["Artist A", "Artist B"]

    # 2. Gom nhom theo thang
    monthly_qs = (
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
            track__artists__name__in=top_artist_names
        )
        .annotate(
            year=ExtractYear('played_at'),
            month=ExtractMonth('played_at'),
        )
        .values('year', 'month', 'track__artists__name')
        .annotate(monthly_plays=Count('id'))
        .order_by('year', 'month')
    )

    # Map month -> artist -> plays
    data_by_month = defaultdict(lambda: defaultdict(int))
    for row in monthly_qs:
        month_str = f"{row['year']:04d}-{row['month']:02d}"
        data_by_month[month_str][row['track__artists__name']] += row['monthly_plays']

    sorted_months = sorted(data_by_month.keys())

    # Dam bao luon co it nhat 2 frame thoi gian hop le
    if len(sorted_months) < 2:
        now_dt = end_dt
        prev_dt = now_dt.replace(day=1) if now_dt.month > 1 else now_dt.replace(year=now_dt.year - 1, month=12, day=1)
        m1 = f"{prev_dt.year:04d}-{prev_dt.month:02d}"
        m2 = f"{now_dt.year:04d}-{now_dt.month:02d}"
        sorted_months = [m1, m2]

    timeline = []
    cumulative_totals = defaultdict(int)

    for m_str in sorted_months:
        month_rankings = []
        for art_name in top_artist_names:
            plays = data_by_month[m_str][art_name]
            cumulative_totals[art_name] += plays
            month_rankings.append({
                "name": art_name,
                "plays": plays,
                "cumulative_plays": cumulative_totals[art_name],
            })
        # Sap xep theo so luot nghe luy ke giam dan
        month_rankings.sort(key=lambda x: x["cumulative_plays"], reverse=True)
        timeline.append({
            "date": m_str,
            "rankings": month_rankings,
        })

    return {
        "metric": "artists",
        "timeline": timeline,
    }

def get_top_albums(user, start_dt, end_dt, limit: int = 10) -> list[dict]:
    """Lay danh sach Top album nghe nhieu nhat trong ky."""
    qs = (
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
            track__album__isnull=False
        )
        .values(
            album_id=F('track__album__spotify_id'),
            album_name=F('track__album__name'),
            image_url=F('track__album__image_url'),
            release_date=F('track__album__release_date'),
        )
        .annotate(play_count=Count('id'))
        .order_by('-play_count')[:limit]
    )

    results = []
    for item in qs:
        alb_id = item['album_id']
        artists = list(
            Artist.objects.filter(albums__spotify_id=alb_id)
            .values_list('name', flat=True)
        )
        if not artists:
            artists = list(
                Artist.objects.filter(tracks__album__spotify_id=alb_id)
                .values_list('name', flat=True)
                .distinct()
            )
        results.append({
            "spotify_id": alb_id,
            "name": item['album_name'],
            "image_url": item['image_url'],
            "release_date": item['release_date'] or "",
            "artists": artists,
            "play_count": item['play_count'],
        })
    return results

def get_weekly_comparison(user, start_dt=None, end_dt=None) -> dict:
    """So sanh so luot nghe hang ngay cua tuan nay so voi tuan truoc."""
    now = timezone.localtime(timezone.now())
    if start_dt and end_dt and (end_dt - start_dt).days <= 7:
        current_week_start = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        current_week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())

    current_week_end = current_week_start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    prev_week_start = current_week_start - timedelta(days=7)
    prev_week_end = current_week_start - timedelta(microseconds=1)

    curr_qs = (
        ListeningHistory.objects.filter(user=user, played_at__range=(current_week_start, current_week_end))
        .annotate(iso_weekday=ExtractIsoWeekDay('played_at'))
        .values('iso_weekday')
        .annotate(count=Count('id'))
    )
    curr_map = {row['iso_weekday']: row['count'] for row in curr_qs}

    prev_qs = (
        ListeningHistory.objects.filter(user=user, played_at__range=(prev_week_start, prev_week_end))
        .annotate(iso_weekday=ExtractIsoWeekDay('played_at'))
        .values('iso_weekday')
        .annotate(count=Count('id'))
    )
    prev_map = {row['iso_weekday']: row['count'] for row in prev_qs}

    day_config = [
        (1, "Thứ 2", "Mon"),
        (2, "Thứ 3", "Tue"),
        (3, "Thứ 4", "Wed"),
        (4, "Thứ 5", "Thu"),
        (5, "Thứ 6", "Fri"),
        (6, "Thứ 7", "Sat"),
        (7, "Chủ Nhật", "Sun"),
    ]

    days = []
    total_curr = 0
    total_prev = 0
    peak_day = "Thứ 2"
    peak_plays = 0

    for idx, name_vi, name_en in day_config:
        c_plays = curr_map.get(idx, 0)
        p_plays = prev_map.get(idx, 0)
        total_curr += c_plays
        total_prev += p_plays
        if c_plays > peak_plays:
            peak_plays = c_plays
            peak_day = name_vi

        days.append({
            "day_index": idx,
            "day_name": name_vi,
            "day_name_en": name_en,
            "current_week_plays": c_plays,
            "previous_week_plays": p_plays,
            "diff": c_plays - p_plays,
        })

    if total_prev > 0:
        growth = round(((total_curr - total_prev) / total_prev) * 100, 1)
    elif total_curr > 0:
        growth = 100.0
    else:
        growth = 0.0

    current_label = f"Tuần này ({current_week_start.strftime('%d/%m')} - {current_week_end.strftime('%d/%m')})"
    prev_label = f"Tuần trước ({prev_week_start.strftime('%d/%m')} - {prev_week_end.strftime('%d/%m')})"

    return {
        "current_week_label": current_label,
        "previous_week_label": prev_label,
        "days": days,
        "summary": {
            "total_current_week": total_curr,
            "total_previous_week": total_prev,
            "growth_percentage": growth,
            "peak_day_current": peak_day,
            "peak_plays_current": peak_plays,
        }
    }

