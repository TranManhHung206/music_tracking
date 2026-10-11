"""
Audio DSP & Multimedia Service
Trich xuat dac trung am thanh truc tiep tu song am 30s bang librosa va dong bo anh nghe si HD tu Deezer/iTunes.
"""

import os
import io
import logging
import tempfile
import requests
import librosa
import numpy as np

from tracker.models import Track, Artist

logger = logging.getLogger(__name__)

def discover_track_multimedia(title: str, artist_name: str) -> dict | None:
    """Tim kiem doan preview 30s va anh nghe si qua Deezer va iTunes."""
    # 1. Deezer API (Uu tien so 1)
    try:
        query = f"{title} {artist_name}"
        resp = requests.get(
            "https://api.deezer.com/search",
            params={"q": query, "limit": 1},
            timeout=7
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            if data:
                item = data[0]
                preview_url = item.get("preview")
                artist_data = item.get("artist", {})
                album_data = item.get("album", {})
                artist_pic = artist_data.get("picture_xl") or artist_data.get("picture_big")
                album_cover = album_data.get("cover_xl") or album_data.get("cover_big")
                if preview_url:
                    return {
                        "source": "deezer",
                        "preview_url": preview_url,
                        "artist_picture": artist_pic,
                        "album_cover": album_cover,
                        "resolved_title": item.get("title"),
                        "resolved_artist": artist_data.get("name"),
                    }
    except Exception as e:
        logger.warning(f"Deezer search error for '{title} - {artist_name}': {e}")

    # 2. iTunes Search API (Du phong so 2)
    try:
        term = f"{title} {artist_name}"
        resp = requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "entity": "song", "limit": 1},
            timeout=7
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                item = results[0]
                preview_url = item.get("previewUrl")
                artwork = item.get("artworkUrl100", "").replace("100x100bb", "1000x1000bb")
                if preview_url:
                    return {
                        "source": "itunes",
                        "preview_url": preview_url,
                        "artist_picture": None,
                        "album_cover": artwork,
                        "resolved_title": item.get("trackName"),
                        "resolved_artist": item.get("artistName"),
                    }
    except Exception as e:
        logger.warning(f"iTunes search error for '{title} - {artist_name}': {e}")

    return None

def extract_dsp_features_from_preview(audio_url: str) -> dict:
    """Tai 30s audio vao tempfile an toan tren Windows va phan tich song am bang librosa."""
    resp = requests.get(audio_url, timeout=10)
    if resp.status_code != 200:
        raise ValueError(f"Khong the tai stream audio: HTTP {resp.status_code}")

    suffix = ".m4a" if "m4a" in audio_url else ".mp3"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(resp.content)
    tmp_path = tmp.name
    tmp.close()

    try:
        y, sr = librosa.load(tmp_path, sr=22050, duration=30)

        # 1. Tempo / BPM thuc te
        tempo_res = librosa.beat.beat_track(y=y, sr=sr)
        raw_bpm = float(tempo_res[0]) if np.ndim(tempo_res[0]) == 0 else float(tempo_res[0][0])
        tempo_score = min(0.98, max(0.1, round(raw_bpm / 180.0, 3)))

        # 2. Energy: RMS Power
        rms = librosa.feature.rms(y=y)[0]
        rms_mean = float(np.mean(rms))
        energy_score = min(0.98, max(0.08, round(rms_mean * 3.8, 3)))

        # 3. Acousticness: Ti le song hai hoa (Harmonic) so voi bo go/dien tu (Percussive)
        y_harm, y_perc = librosa.effects.hpss(y)
        harm_energy = float(np.sum(y_harm ** 2))
        perc_energy = float(np.sum(y_perc ** 2)) + 1e-6
        h_p_ratio = harm_energy / (harm_energy + perc_energy)
        flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        acoustic_score = min(0.98, max(0.05, round(h_p_ratio * (1.0 - flatness * 1.5), 3)))

        # 4. Danceability: Onset strength & beat regularity
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        pulse = librosa.beat.plp(onset_envelope=onset_env, sr=sr)
        pulse_strength = float(np.mean(pulse))
        danceability_score = min(0.95, max(0.20, round(pulse_strength * 1.8, 3)))

        # 5. Valence: Phan tich Chroma Major vs Minor tonality & do sang am thanh
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        brightness = float(np.mean(spectral_centroid)) / 4500.0
        valence_score = min(0.95, max(0.15, round(0.4 * brightness + 0.6 * np.mean(chroma), 3)))

        return {
            "bpm": round(raw_bpm, 1),
            "energy": energy_score,
            "acousticness": acoustic_score,
            "danceability": danceability_score,
            "valence": valence_score,
            "tempo_score": tempo_score,
        }
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def enrich_track_with_dsp_and_artwork(track: Track, sync_artist_image: bool = True) -> bool:
    """Phan tich am thanh that tu song am 30s va cap nhat anh nghe si HD cho ban ghi Track."""
    artist_names = [a.name for a in track.artists.all()]
    first_artist = artist_names[0] if artist_names else ""

    assets = discover_track_assets_safe(track.name, first_artist)

    # 1. Cap nhat anh nghe si tu ben ngoai chi khi nghe si chua tung co anh va khong ghi de anh Spotify
    if sync_artist_image and assets and assets.get("artist_picture"):
        artist_pic = assets["artist_picture"]
        first_artist_obj = track.artists.first()
        if first_artist_obj and not first_artist_obj.image_url:
            first_artist_obj.image_url = artist_pic
            first_artist_obj.save(update_fields=["image_url"])

    # 2. Trich xuat Audio Features tu song am 30s
    if assets and assets.get("preview_url"):
        try:
            dsp_res = extract_dsp_features_from_preview(assets["preview_url"])
            track.danceability = dsp_res["danceability"]
            track.energy = dsp_res["energy"]
            track.valence = dsp_res["valence"]
            track.acousticness = dsp_res["acousticness"]
            track.tempo = dsp_res["bpm"]
            track.features_synced = True
            track.save(update_fields=["danceability", "energy", "valence", "acousticness", "tempo", "features_synced"])
            return True
        except Exception as e:
            logger.warning(f"Loi phan tich DSP cho track '{track.name}': {e}. Su dung fallback phỏng đoán.")

    # 3. Fallback Heuristic phong doan neu khong tim thay link 30s hoac gap loi giai ma
    from tracker.services.ingestion import estimate_track_audio_features
    estimated = estimate_track_audio_features(track)
    track.danceability = estimated["danceability"]
    track.energy = estimated["energy"]
    track.valence = estimated["valence"]
    track.acousticness = estimated["acousticness"]
    track.tempo = estimated["tempo"]
    track.features_synced = True
    track.save(update_fields=["danceability", "energy", "valence", "acousticness", "tempo", "features_synced"])
    return False

def discover_track_assets_safe(title: str, artist_name: str) -> dict | None:
    """Wrapper an toan cho ham tim kiem tai nguyen."""
    return discover_track_multimedia(title, artist_name)
