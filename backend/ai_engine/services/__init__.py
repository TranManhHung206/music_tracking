"""
Export cac services cua app ai_engine:
- ai_persona: Goi AI Inference (Groq, Gemini, Heuristic) de sinh bao cao AI Music Persona.
- knn_recommender: KNN Cosine Distance tinh toan bai hat co Audio Features tuong dong.
"""

from .ai_persona import (
    generate_and_save_persona,
    extract_user_music_context,
    generate_heuristic_persona,
)
from .knn_recommender import (
    get_song_recommendations,
    extract_track_vector,
    normalize_tempo,
)
from .facts_agent import (
    get_or_generate_music_facts,
    run_music_facts_agent,
    generate_heuristic_facts,
)

__all__ = [
    'generate_and_save_persona',
    'extract_user_music_context',
    'generate_heuristic_persona',
    'get_song_recommendations',
    'extract_track_vector',
    'normalize_tempo',
    'get_or_generate_music_facts',
    'run_music_facts_agent',
    'generate_heuristic_facts',
]
