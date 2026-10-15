"""
KNN Song Recommendation Engine
Su dung scikit-learn NearestNeighbors voi Weighted Euclidean Distance (KD-Tree / Auto) de tim kiem cac bai hat co Audio Features tuong dong nhat.
Vector 5D: [danceability, energy, valence, acousticness, normalized_tempo].
"""

import numpy as np
from sklearn.neighbors import NearestNeighbors
from tracker.models import Track

# Bang trong so dac trung am thanh (Feature Weights)
# [danceability, energy, valence, acousticness, tempo_norm]
# Can bang tu nhien giua acoustic va electronic ma khong lam bias the loai
FEATURE_WEIGHTS = np.array([1.0, 1.1, 0.8, 1.1, 1.2], dtype=float)
SQRT_WEIGHTS = np.sqrt(FEATURE_WEIGHTS)
MAX_WEIGHTED_DISTANCE = float(np.sqrt(np.sum(FEATURE_WEIGHTS)))

def normalize_tempo(tempo_bpm: float) -> float:
    """Chuan hoa tempo BPM (40 - 220) ve mien [0.0, 1.0]."""
    if not tempo_bpm or tempo_bpm <= 0:
        return 0.5
    norm = (float(tempo_bpm) - 40.0) / 180.0
    return round(min(max(norm, 0.0), 1.0), 4)

def extract_track_vector(track: Track) -> list[float]:
    """Trich xuat vector dac trung am thanh 5 chieu [d, e, v, a, t]."""
    d = min(max(float(track.danceability or 0.0), 0.0), 1.0)
    e = min(max(float(track.energy or 0.0), 0.0), 1.0)
    v = min(max(float(track.valence or 0.0), 0.0), 1.0)
    a = min(max(float(track.acousticness or 0.0), 0.0), 1.0)
    t = normalize_tempo(track.tempo)
    return [d, e, v, a, t]

def apply_feature_weights(raw_vector: list[float] | np.ndarray) -> np.ndarray:
    """Bien doi vector dac trung bang sqrt(weights) de tinh Euclidean tuong duong Weighted Euclidean."""
    return np.array(raw_vector, dtype=float) * SQRT_WEIGHTS

def get_song_recommendations(seed_track_identifier: str, top_k: int = 5) -> dict:
    """
    Tim kiem Top K bai hat tuong dong nhat voi seed_track dua tren khoang cach Weighted Euclidean.
    seed_track_identifier: spotify_id hoac primary key cua Track.
    """
    # 1. Tim seed track
    seed_track = (
        Track.objects.filter(spotify_id=seed_track_identifier).first()
        or Track.objects.filter(id=seed_track_identifier if str(seed_track_identifier).isdigit() else None).first()
    )

    if not seed_track:
        raise ValueError(f"Khong tim thay bai hat voi ma {seed_track_identifier}")

    seed_vector = extract_track_vector(seed_track)
    seed_artists = list(seed_track.artists.values_list('name', flat=True))

    seed_info = {
        "spotify_id": seed_track.spotify_id,
        "name": seed_track.name,
        "artists": seed_artists,
        "album": seed_track.album.name if seed_track.album else "",
        "image_url": seed_track.album.image_url if seed_track.album else "",
        "audio_features": {
            "danceability": seed_track.danceability,
            "energy": seed_track.energy,
            "valence": seed_track.valence,
            "acousticness": seed_track.acousticness,
            "tempo": seed_track.tempo,
        }
    }

    # 2. Lay toan bo cac track da dong bo features de huan luyen KNN
    candidate_tracks = list(
        Track.objects.filter(features_synced=True)
        .prefetch_related('artists')
        .select_related('album')
    )

    # Neu he thong chua co du tracks, them cac tracks co san bat ke flag features_synced de phuc vu test
    if len(candidate_tracks) < 2:
        candidate_tracks = list(
            Track.objects.all()
            .prefetch_related('artists')
            .select_related('album')
        )

    # Neu chi co dung 1 track hoac khong co track nao khac
    other_candidates = [t for t in candidate_tracks if t.id != seed_track.id]
    if not other_candidates:
        return {
            "seed_track": seed_info,
            "recommendations": [],
        }

    # 3. Chuan bi ma tran vector co trong so cho cac candidates
    candidate_vectors = [apply_feature_weights(extract_track_vector(t)) for t in other_candidates]
    matrix = np.array(candidate_vectors)

    # 4. Fit mo hinh NearestNeighbors voi Euclidean Distance va thuat toan KD-Tree/Auto
    query_k = min(max(top_k * 3, top_k), len(other_candidates))
    model = NearestNeighbors(n_neighbors=query_k, metric='euclidean', algorithm='auto')
    model.fit(matrix)

    # 5. Truy van khoang cach
    seed_weighted = apply_feature_weights(seed_vector).reshape(1, -1)
    distances, indices = model.kneighbors(seed_weighted, n_neighbors=query_k)

    recommendations = []
    seen_track_signatures = set()
    for dist, idx in zip(distances[0], indices[0]):
        matched_track = other_candidates[idx]

        # Deduplication tranh goi y cung 1 ten bai hat nhieu lan
        primary_artist = matched_track.artists.first()
        primary_artist_name = primary_artist.name.lower().strip() if primary_artist else ""
        signature = (matched_track.name.lower().strip(), primary_artist_name)
        if signature in seen_track_signatures:
            continue
        seen_track_signatures.add(signature)

        # Do tuong dong Weighted Euclidean: [0.0, 1.0]
        raw_sim = 1.0 - (float(dist) / MAX_WEIGHTED_DISTANCE)
        similarity = round(min(max(raw_sim, 0.0), 1.0), 3)

        recommendations.append({
            "spotify_id": matched_track.spotify_id,
            "name": matched_track.name,
            "artists": list(matched_track.artists.values_list('name', flat=True)),
            "album": matched_track.album.name if matched_track.album else "",
            "image_url": matched_track.album.image_url if matched_track.album else "",
            "similarity_score": similarity,
        })
        if len(recommendations) >= top_k:
            break

    # Sap xep giam dan theo similarity_score
    recommendations.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {
        "seed_track": seed_info,
        "recommendations": recommendations,
    }
