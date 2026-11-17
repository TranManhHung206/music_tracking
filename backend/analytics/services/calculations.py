"""
Analytics Calculations Service
Thuc thi cac truy van tong hop hieu nang cao cap Database bang Django ORM:
Summary, Top Tracks, Top Artists, Audio Features Radar, Listening Heatmap va Bar Chart Race.
"""

import calendar
from datetime import datetime, time, timedelta, date
from collections import defaultdict
from django.utils import timezone
from django.db.models import Count, Avg, Sum, F
from django.db.models.functions import ExtractIsoWeekDay, ExtractHour, ExtractYear, ExtractMonth, TruncDate
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

    unique_artists_count = qs.filter(track__artists__isnull=False).values('track__artists').distinct().count()
    unique_albums_count = qs.filter(track__album__isnull=False).values('track__album').distinct().count()

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
    "vương anh tú", "ronboogz", "coldzy", "gill", "tage", "vsoul", "rhyder",
    "hoaprox", "masew", "touliver", "slimv", "triple d"
}

VPOP_KEYWORDS = [
    "3 1 0 7", "3107", "10005", "3000km", "good4us", "damsay", "daybyday",
    "ngayquangay", "tinhco", "vanvuong", "say hi", "anh trai", "chị đẹp",
    "rap viet", "chuyện rằng", "lời tạm biệt", "người hay nói"
]

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
import threading
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_ALL_CSV_ARTIST_NAMES = set()
_CSV_WRITE_LOCK = threading.Lock()

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

                    _ALL_CSV_ARTIST_NAMES.add(artist_name)

                    # Neu cot notes danh dau la 'new' thi bo qua, khong phan loai vao vn hoac foreign
                    notes_val = row_clean.get("notes", "").strip().lower()
                    if notes_val == "new":
                        continue

                    if type_col:
                        raw_val = row_clean.get(type_col, "").strip().lower()
                        # Xu ly cac dinh dang 1.0, 1, true, vn
                        if raw_val in ["1", "1.0", "true", "yes", "vn", "vietnam", "viet nam", "vpop", "v-pop", "viet", "trong nuoc"]:
                            vn_artists.add(artist_name)
                        elif raw_val in ["0", "0.0", "false", "no", "foreign", "quoc te", "international", "usuk", "us-uk", "kpop"]:
                            foreign_artists.add(artist_name)
                        elif raw_val:
                            vn_artists.add(artist_name)
                    else:
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
        was_loaded = _CUSTOM_ARTISTS_LOADED
        if not _CUSTOM_ARTISTS_LOADED or current_mtime != _LAST_CSV_MTIME:
            vn, foreign = load_custom_artist_dataset()
            VPOP_ARTISTS.update(vn)
            USUK_ARTISTS.update(foreign)
            _CUSTOM_ARTISTS_LOADED = True
            _LAST_CSV_MTIME = current_mtime
            if was_loaded:
                try:
                    from django.contrib.auth.models import User
                    from analytics.services.caching import invalidate_user_analytics_cache
                    for uid in User.objects.values_list('id', flat=True):
                        invalidate_user_analytics_cache(uid)
                except Exception:
                    pass
    except Exception:
        pass

ensure_custom_artists_loaded()

def register_unclassified_artists_batch(artist_names) -> int:
    """Tu dong ghi nhan cac nghe si chua co trong CSV voi gia tri mac dinh 0 va note la New."""
    global _LAST_CSV_MTIME
    ensure_custom_artists_loaded()

    if not artist_names:
        return 0

    new_names = []
    for name in artist_names:
        if not name or not isinstance(name, str):
            continue
        cleaned = name.strip()
        if not cleaned or cleaned.lower() == "unknown artist":
            continue
        if cleaned.lower() not in _ALL_CSV_ARTIST_NAMES:
            _ALL_CSV_ARTIST_NAMES.add(cleaned.lower())
            new_names.append(cleaned)

    if not new_names:
        return 0

    if not DATA_DIR.exists():
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    target_csv = DATA_DIR / "vietnamese_artist.csv"
    with _CSV_WRITE_LOCK:
        try:
            file_exists = target_csv.exists() and target_csv.stat().st_size > 0
            needs_newline = False
            if file_exists:
                with open(target_csv, mode="rb") as rf:
                    rf.seek(max(0, target_csv.stat().st_size - 2))
                    tail = rf.read()
                    if tail and not tail.endswith((b"\n", b"\r")):
                        needs_newline = True

            with open(target_csv, mode="a", encoding="utf-8-sig", newline="") as f:
                if needs_newline:
                    f.write("\n")
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["spotify_name", "is_vpop", "notes"])
                for n in new_names:
                    writer.writerow([n, "0", "New"])
            _LAST_CSV_MTIME = target_csv.stat().st_mtime
            return len(new_names)
        except Exception:
            return 0

def register_unclassified_artist(artist_name: str) -> bool:
    """Ghi nhan mot nghe si don le vao CSV neu chua ton tai."""
    return register_unclassified_artists_batch([artist_name]) > 0

def is_artist_match(artist_name_lower: str, target_name: str) -> bool:
    """Kiem tra ten nghe si khop theo tu rieng biet tranh loi substring."""
    pattern = r'\b' + re.escape(target_name.lower()) + r'\b'
    return bool(re.search(pattern, artist_name_lower))

def classify_artist_genres(artist_name: str, track_name: str = "", artists: list = None, track = None, auto_register: bool = False) -> str:
    """
    Phan loai the loai am nhac lai (Hybrid Genre Classification) ket hop giua
    sieu du lieu (Metadata: ten nghe si, ngon ngu) va dac trung song am (Audio DSP Features).
    """
    ensure_custom_artists_loaded()
    title = track_name or ""
    title_lower = title.lower()

    if artists:
        artist_names_lower = [a.lower() for a in artists if a]
        check_artists = artists
    elif artist_name:
        artist_names_lower = [artist_name.lower()]
        check_artists = [artist_name]
    else:
        artist_names_lower = []
        check_artists = []

    if auto_register and check_artists:
        unregistered = [a for a in check_artists if a and a.strip().lower() not in _ALL_CSV_ARTIST_NAMES]
        if unregistered:
            register_unclassified_artists_batch(unregistered)

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
        return "V-Pop"

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
        "V-Pop": "#EC4899",
        "EDM / Electronic": "#1DB954",
        "Acoustic / Lo-Fi": "#10B981",
        "Phonk / High Energy": "#E11D48",
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
    """Tinh toan 5 dac tinh am thanh chuan hoa [0.0, 1.0] kem nguon goc du lieu cho bieu do Radar."""
    qs = ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt))
    total_tracks = qs.count()

    stats = qs.aggregate(
        avg_valence=Avg('track__valence'),
        avg_energy=Avg('track__energy'),
        avg_danceability=Avg('track__danceability'),
        avg_acousticness=Avg('track__acousticness'),
        avg_tempo=Avg('track__tempo'),
    )

    raw_valence = stats.get('avg_valence') if stats.get('avg_valence') is not None else 0.5
    raw_energy = stats.get('avg_energy') if stats.get('avg_energy') is not None else 0.5
    raw_danceability = stats.get('avg_danceability') if stats.get('avg_danceability') is not None else 0.5
    raw_acousticness = stats.get('avg_acousticness') if stats.get('avg_acousticness') is not None else 0.5
    raw_tempo = stats.get('avg_tempo') if stats.get('avg_tempo') is not None else 120.0

    # Chuan hoa BPM ve [0.0, 1.0] (tempo chia cho 200)
    norm_tempo = min(max(raw_tempo / 200.0, 0.0), 1.0)

    source_qs = qs.values('track__features_source').annotate(cnt=Count('id'))
    source_counts = {
        (row['track__features_source'] or 'unavailable'): row['cnt']
        for row in source_qs
    }
    spotify_cnt = source_counts.get('spotify', 0)
    dsp_cnt = source_counts.get('dsp_preview', 0)
    estimated_cnt = source_counts.get('estimated', 0)
    legacy_cnt = source_counts.get('legacy_unknown', 0)
    unavailable_cnt = source_counts.get('unavailable', 0)
    measured_cnt = spotify_cnt + dsp_cnt
    measured_pct = round((measured_cnt / total_tracks) * 100, 1) if total_tracks > 0 else 0.0

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
        "provenance": {
            "spotify": spotify_cnt,
            "dsp_preview": dsp_cnt,
            "estimated": estimated_cnt,
            "legacy_unknown": legacy_cnt,
            "unavailable": unavailable_cnt,
            "total_plays": total_tracks,
            "measured_percentage": measured_pct,
            "has_estimates": estimated_cnt > 0,
            "has_legacy_unknown": legacy_cnt > 0,
        },
    }

def _build_month_calendar(start_date: date, end_date: date, daily_map: dict) -> dict:
    """Xay dung du lieu lich thang (gioi han nghiem ngat dung 1 thang tu ngay 1 den ngay cuoi thang)."""
    month_start = date(start_date.year, start_date.month, 1)
    last_day_num = calendar.monthrange(start_date.year, start_date.month)[1]
    month_end = date(start_date.year, start_date.month, last_day_num)

    curr = month_start
    days = []
    max_count = 0
    total_plays = 0
    peak_day = None
    peak_plays = 0
    active_days = 0

    first_day_weekday = month_start.isoweekday()

    while curr <= month_end:
        cnt = daily_map.get(curr, 0)
        total_plays += cnt
        if cnt > 0:
            active_days += 1
        if cnt > peak_plays:
            peak_plays = cnt
            peak_day = curr.strftime('%Y-%m-%d')
        if cnt > max_count:
            max_count = cnt

        days.append({
            "date": curr.strftime('%Y-%m-%d'),
            "day_number": curr.day,
            "day_of_week": curr.isoweekday(),
            "count": cnt,
            "is_current_month": True,
        })
        curr += timedelta(days=1)

    return {
        "year": start_date.year,
        "month": start_date.month,
        "first_day_weekday": first_day_weekday,
        "total_days": len(days),
        "total_plays": total_plays,
        "peak_day": peak_day or (month_start.strftime('%Y-%m-%d') if days else ""),
        "peak_plays": peak_plays,
        "active_days": active_days,
        "max_density": max_count,
        "days": days,
    }

def _build_year_calendar(start_date: date, end_date: date, daily_map: dict) -> dict:
    """Xay dung du lieu lich nam (53 tuan x 7 ngay) dang contribution graph."""
    monday_start = start_date - timedelta(days=start_date.isoweekday() - 1)
    sunday_end = end_date + timedelta(days=7 - end_date.isoweekday())

    curr = monday_start
    days = []
    max_count = 0
    total_plays = 0
    peak_day = None
    peak_plays = 0
    active_days = 0
    current_streak = 0
    max_streak = 0

    months_seen = set()
    months_header = []
    month_plays = defaultdict(int)

    while curr <= sunday_end:
        week_idx = (curr - monday_start).days // 7
        is_in_range = (start_date <= curr <= end_date)
        cnt = daily_map.get(curr, 0) if is_in_range else 0

        if is_in_range:
            total_plays += cnt
            month_plays[curr.month] += cnt
            if cnt > 0:
                active_days += 1
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0

            if cnt > peak_plays:
                peak_plays = cnt
                peak_day = curr.strftime('%Y-%m-%d')
            if cnt > max_count:
                max_count = cnt

            if curr.month not in months_seen:
                months_seen.add(curr.month)
                months_header.append({
                    "month": curr.month,
                    "label": f"T{curr.month}",
                    "start_week": week_idx,
                })

        days.append({
            "date": curr.strftime('%Y-%m-%d'),
            "month": curr.month,
            "day_number": curr.day,
            "day_of_week": curr.isoweekday(),
            "week_index": week_idx,
            "count": cnt,
            "is_in_range": is_in_range,
        })
        curr += timedelta(days=1)

    top_month = max(month_plays.items(), key=lambda x: x[1])[0] if month_plays else (start_date.month if start_date else 1)

    return {
        "year": start_date.year,
        "total_weeks": (sunday_end - monday_start).days // 7 + 1,
        "total_days": len(days),
        "total_plays": total_plays,
        "peak_day": peak_day or (start_date.strftime('%Y-%m-%d') if days else ""),
        "peak_plays": peak_plays,
        "active_days": active_days,
        "longest_streak": max_streak,
        "top_month": top_month,
        "top_month_plays": month_plays.get(top_month, 0),
        "max_density": max_count,
        "months_header": months_header,
        "days": days,
    }

def get_listening_heatmap(user, start_dt, end_dt, time_range_label: str = '30d', period_type: str = None) -> dict:
    """Trich xuat ma tran mat do nghe nhac thich ung (Tuan / Thang / Nam)."""
    user_tz = timezone.get_current_timezone()

    # Xac dinh period_type neu chua chi dinh ro
    if not period_type:
        day_diff = (end_dt - start_dt).days
        if day_diff > 35:
            period_type = 'year'
        elif day_diff > 8:
            period_type = 'month'
        else:
            period_type = 'week'

    # 1. Luon trich xuat ma tran 7x24 de dam bao tinh tuong thich nguoc tuyet doi
    qs = (
        ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt))
        .annotate(
            day_of_week=ExtractIsoWeekDay('played_at', tzinfo=user_tz),
            hour=ExtractHour('played_at', tzinfo=user_tz),
        )
        .values('day_of_week', 'hour')
        .annotate(count=Count('id'))
        .order_by('day_of_week', 'hour')
    )

    matrix_map = {(item['day_of_week'], item['hour']): item['count'] for item in qs}
    matrix = []
    max_density = 0

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

    result = {
        "time_range": time_range_label,
        "period_type": period_type,
        "max_density": max_density,
        "matrix": matrix,
    }

    # 2. Xay dung lich theo chu ky Thang hoac Nam neu duoc yeu cau
    if period_type in ('month', 'year'):
        qs_daily = (
            ListeningHistory.objects.filter(user=user, played_at__range=(start_dt, end_dt))
            .annotate(play_date=TruncDate('played_at', tzinfo=user_tz))
            .values('play_date')
            .annotate(count=Count('id'))
            .order_by('play_date')
        )
        daily_map = {item['play_date']: item['count'] for item in qs_daily if item['play_date']}

        start_date = timezone.localtime(start_dt, user_tz).date() if timezone.is_aware(start_dt) else start_dt.date()
        end_date = timezone.localtime(end_dt, user_tz).date() if timezone.is_aware(end_dt) else end_dt.date()

        if period_type == 'month':
            # Phong ve: Neu truyen vao khoang thoi gian dai hon 32 ngay (do mang dai ngay cua nam sang thang),
            # chi tap trung vao thang cua end_date
            if (end_date - start_date).days > 32:
                target_year = end_date.year
                target_month = end_date.month
                start_date = date(target_year, target_month, 1)
                last_day_num = calendar.monthrange(target_year, target_month)[1]
                end_date = date(target_year, target_month, last_day_num)

            result["month_calendar"] = _build_month_calendar(start_date, end_date, daily_map)
        elif period_type == 'year':
            result["year_calendar"] = _build_year_calendar(start_date, end_date, daily_map)

    return result

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

    # 2. Gom nhom theo thang theo mui gio nguoi dung
    user_tz = timezone.get_current_timezone()
    monthly_qs = (
        ListeningHistory.objects.filter(
            user=user,
            played_at__range=(start_dt, end_dt),
            track__artists__name__in=top_artist_names
        )
        .annotate(
            year=ExtractYear('played_at', tzinfo=user_tz),
            month=ExtractMonth('played_at', tzinfo=user_tz),
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

def _build_comparison_summary(total_curr: int, total_prev: int, peak_label: str, peak_plays: int) -> dict:
    """Tinh toan chi so tong hop va trang thai moc nen (baseline_status) cho bieu do so sanh."""
    if total_prev > 0:
        growth = round(((total_curr - total_prev) / total_prev) * 100, 1)
        baseline_status = "normal"
    elif total_curr > 0:
        growth = None
        baseline_status = "new_activity"
    else:
        growth = 0.0
        baseline_status = "empty"

    return {
        "total_current": total_curr,
        "total_previous": total_prev,
        "total_current_week": total_curr,
        "total_previous_week": total_prev,
        "growth_percentage": growth,
        "baseline_status": baseline_status,
        "peak_label": peak_label,
        "peak_plays": peak_plays,
        "peak_day_current": peak_label,
        "peak_plays_current": peak_plays,
    }


def get_weekly_comparison(user, start_dt=None, end_dt=None, period_type: str = None) -> dict:
    """
    So sanh xu huong luot nghe thich ung theo ky duoc chon (Tuan / Thang / Nam)
    doi chieu voi ky tuong duong lien truoc theo dung mui gio hien tai.
    """
    user_tz = timezone.get_current_timezone()
    today_local = timezone.localdate()

    local_start_date = None
    local_end_date = None
    if start_dt and end_dt:
        local_start_date = (timezone.localtime(start_dt, user_tz) if timezone.is_aware(start_dt) else start_dt).date()
        local_end_date = (timezone.localtime(end_dt, user_tz) if timezone.is_aware(end_dt) else end_dt).date()

    resolved_type = (period_type or "").lower()
    if resolved_type not in ("week", "month", "year"):
        if local_start_date and local_end_date:
            span_days = (local_end_date - local_start_date).days
            if span_days <= 8:
                resolved_type = "week"
            elif span_days <= 35:
                resolved_type = "month"
            else:
                resolved_type = "year"
        else:
            resolved_type = "week"

    if resolved_type == "month":
        if local_start_date and local_end_date:
            target_date = local_end_date if (local_end_date - local_start_date).days > 32 else local_start_date
        else:
            target_date = today_local

        y, m = target_date.year, target_date.month
        py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
        curr_last_day = calendar.monthrange(y, m)[1]
        prev_last_day = calendar.monthrange(py, pm)[1]

        curr_start = timezone.make_aware(datetime.combine(date(y, m, 1), time.min), user_tz)
        curr_end = timezone.make_aware(datetime.combine(date(y, m, curr_last_day), time.max), user_tz)
        prev_start = timezone.make_aware(datetime.combine(date(py, pm, 1), time.min), user_tz)
        prev_end = timezone.make_aware(datetime.combine(date(py, pm, prev_last_day), time.max), user_tz)

        curr_qs = (
            ListeningHistory.objects.filter(user=user, played_at__range=(curr_start, curr_end))
            .annotate(play_date=TruncDate('played_at', tzinfo=user_tz))
            .values('play_date')
            .annotate(count=Count('id'))
        )
        prev_qs = (
            ListeningHistory.objects.filter(user=user, played_at__range=(prev_start, prev_end))
            .annotate(play_date=TruncDate('played_at', tzinfo=user_tz))
            .values('play_date')
            .annotate(count=Count('id'))
        )

        curr_buckets = defaultdict(int)
        for row in curr_qs:
            if row['play_date']:
                b_idx = min(((row['play_date'].day - 1) // 7) + 1, 5)
                curr_buckets[b_idx] += row['count']

        prev_buckets = defaultdict(int)
        for row in prev_qs:
            if row['play_date']:
                b_idx = min(((row['play_date'].day - 1) // 7) + 1, 5)
                prev_buckets[b_idx] += row['count']

        max_tail_day = max(curr_last_day, prev_last_day)
        bucket_defs = [
            (1, "Tuần 1 (01-07)", "T1 (1-7)", "Ngày 01-07"),
            (2, "Tuần 2 (08-14)", "T2 (8-14)", "Ngày 08-14"),
            (3, "Tuần 3 (15-21)", "T3 (15-21)", "Ngày 15-21"),
            (4, "Tuần 4 (22-28)", "T4 (22-28)", "Ngày 22-28"),
        ]
        if max_tail_day >= 29:
            bucket_defs.append((5, f"Cuối tháng (29-{max_tail_day})", f"29-{max_tail_day}", f"Ngày 29-{max_tail_day}"))

        series = []
        days_compat = []
        total_curr = 0
        total_prev = 0
        peak_label = bucket_defs[0][1]
        peak_plays = 0

        for idx, full_label, short_label, sub_label in bucket_defs:
            c_plays = curr_buckets.get(idx, 0)
            p_plays = prev_buckets.get(idx, 0)
            total_curr += c_plays
            total_prev += p_plays
            if c_plays > peak_plays:
                peak_plays = c_plays
                peak_label = full_label

            series.append({
                "index": idx,
                "label": full_label,
                "short_label": short_label,
                "full_label": sub_label,
                "current_plays": c_plays,
                "previous_plays": p_plays,
                "diff": c_plays - p_plays,
            })
            days_compat.append({
                "day_index": idx,
                "day_name": short_label,
                "day_name_en": full_label,
                "current_week_plays": c_plays,
                "previous_week_plays": p_plays,
                "diff": c_plays - p_plays,
            })

        current_label = f"Tháng {m:02d}/{y}"
        previous_label = f"Tháng {pm:02d}/{py}"

        return {
            "period_type": "month",
            "granularity": "week_of_month",
            "current_label": current_label,
            "previous_label": previous_label,
            "current_week_label": current_label,
            "previous_week_label": previous_label,
            "series": series,
            "days": days_compat,
            "summary": _build_comparison_summary(total_curr, total_prev, peak_label, peak_plays),
        }

    if resolved_type == "year":
        target_year = local_start_date.year if local_start_date else today_local.year
        prev_year = target_year - 1

        curr_start = timezone.make_aware(datetime.combine(date(target_year, 1, 1), time.min), user_tz)
        curr_end = timezone.make_aware(datetime.combine(date(target_year, 12, 31), time.max), user_tz)
        prev_start = timezone.make_aware(datetime.combine(date(prev_year, 1, 1), time.min), user_tz)
        prev_end = timezone.make_aware(datetime.combine(date(prev_year, 12, 31), time.max), user_tz)

        curr_qs = (
            ListeningHistory.objects.filter(user=user, played_at__range=(curr_start, curr_end))
            .annotate(play_month=ExtractMonth('played_at', tzinfo=user_tz))
            .values('play_month')
            .annotate(count=Count('id'))
        )
        prev_qs = (
            ListeningHistory.objects.filter(user=user, played_at__range=(prev_start, prev_end))
            .annotate(play_month=ExtractMonth('played_at', tzinfo=user_tz))
            .values('play_month')
            .annotate(count=Count('id'))
        )

        curr_map = {row['play_month']: row['count'] for row in curr_qs if row['play_month']}
        prev_map = {row['play_month']: row['count'] for row in prev_qs if row['play_month']}

        series = []
        days_compat = []
        total_curr = 0
        total_prev = 0
        peak_label = "Tháng 1"
        peak_plays = 0

        for m_idx in range(1, 13):
            c_plays = curr_map.get(m_idx, 0)
            p_plays = prev_map.get(m_idx, 0)
            total_curr += c_plays
            total_prev += p_plays
            full_label = f"Tháng {m_idx}"
            short_label = f"T{m_idx}"
            if c_plays > peak_plays:
                peak_plays = c_plays
                peak_label = full_label

            series.append({
                "index": m_idx,
                "label": full_label,
                "short_label": short_label,
                "full_label": f"{full_label}/{target_year}",
                "current_plays": c_plays,
                "previous_plays": p_plays,
                "diff": c_plays - p_plays,
            })
            days_compat.append({
                "day_index": m_idx,
                "day_name": short_label,
                "day_name_en": full_label,
                "current_week_plays": c_plays,
                "previous_week_plays": p_plays,
                "diff": c_plays - p_plays,
            })

        current_label = f"Năm {target_year}"
        previous_label = f"Năm {prev_year}"

        return {
            "period_type": "year",
            "granularity": "month",
            "current_label": current_label,
            "previous_label": previous_label,
            "current_week_label": current_label,
            "previous_week_label": previous_label,
            "series": series,
            "days": days_compat,
            "summary": _build_comparison_summary(total_curr, total_prev, peak_label, peak_plays),
        }

    # Che do Tuan (mac dinh): So sanh 7 ngay (Thu 2 - Chu Nhat) cua tuan duoc chon voi tuan lien truoc
    if local_start_date and local_end_date and (local_end_date - local_start_date).days <= 7:
        anchor_date = local_end_date if local_start_date.weekday() != 0 else local_start_date
        curr_monday = anchor_date - timedelta(days=anchor_date.weekday())
    else:
        curr_monday = today_local - timedelta(days=today_local.weekday())

    curr_sunday = curr_monday + timedelta(days=6)
    prev_monday = curr_monday - timedelta(days=7)
    prev_sunday = prev_monday + timedelta(days=6)

    current_week_start = timezone.make_aware(datetime.combine(curr_monday, time.min), user_tz)
    current_week_end = timezone.make_aware(datetime.combine(curr_sunday, time.max), user_tz)
    prev_week_start = timezone.make_aware(datetime.combine(prev_monday, time.min), user_tz)
    prev_week_end = timezone.make_aware(datetime.combine(prev_sunday, time.max), user_tz)

    curr_qs = (
        ListeningHistory.objects.filter(user=user, played_at__range=(current_week_start, current_week_end))
        .annotate(iso_weekday=ExtractIsoWeekDay('played_at', tzinfo=user_tz))
        .values('iso_weekday')
        .annotate(count=Count('id'))
    )
    curr_map = {row['iso_weekday']: row['count'] for row in curr_qs}

    prev_qs = (
        ListeningHistory.objects.filter(user=user, played_at__range=(prev_week_start, prev_week_end))
        .annotate(iso_weekday=ExtractIsoWeekDay('played_at', tzinfo=user_tz))
        .values('iso_weekday')
        .annotate(count=Count('id'))
    )
    prev_map = {row['iso_weekday']: row['count'] for row in prev_qs}

    day_config = [
        (1, "Thứ 2", "T2", "Mon"),
        (2, "Thứ 3", "T3", "Tue"),
        (3, "Thứ 4", "T4", "Wed"),
        (4, "Thứ 5", "T5", "Thu"),
        (5, "Thứ 6", "T6", "Fri"),
        (6, "Thứ 7", "T7", "Sat"),
        (7, "Chủ Nhật", "CN", "Sun"),
    ]

    days = []
    series = []
    total_curr = 0
    total_prev = 0
    peak_day = "Thứ 2"
    peak_plays = 0

    for idx, name_vi, short_vi, name_en in day_config:
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
        series.append({
            "index": idx,
            "label": name_vi,
            "short_label": short_vi,
            "full_label": f"{name_vi} ({(curr_monday + timedelta(days=idx - 1)).strftime('%d/%m')})",
            "current_plays": c_plays,
            "previous_plays": p_plays,
            "diff": c_plays - p_plays,
        })

    this_monday = today_local - timedelta(days=today_local.weekday())
    is_current_week = (curr_monday == this_monday)
    _, iso_w, _ = curr_monday.isocalendar()
    _, prev_iso_w, _ = prev_monday.isocalendar()

    curr_prefix = "Tuần này" if is_current_week else f"Tuần {iso_w}"
    prev_prefix = "Tuần trước" if is_current_week else f"Tuần {prev_iso_w}"
    current_label = f"{curr_prefix} ({curr_monday.strftime('%d/%m')} - {curr_sunday.strftime('%d/%m')})"
    previous_label = f"{prev_prefix} ({prev_monday.strftime('%d/%m')} - {prev_sunday.strftime('%d/%m')})"

    return {
        "period_type": "week",
        "granularity": "day",
        "current_label": current_label,
        "previous_label": previous_label,
        "current_week_label": current_label,
        "previous_week_label": previous_label,
        "series": series,
        "days": days,
        "summary": _build_comparison_summary(total_curr, total_prev, peak_day, peak_plays),
    }

