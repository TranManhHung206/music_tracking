"""
URL routing cho app ai_engine:
- persona/generate/
- persona/latest/
- persona/history/
- recommendations/
"""

from django.urls import path
from .views import (
    PersonaGenerateView,
    PersonaLatestView,
    PersonaHistoryView,
    SongRecommendationsView,
    MusicFactsView,
    CodebaseQueryView,
    CodebaseIndexView,
)

app_name = 'ai_engine'

urlpatterns = [
    path('persona/generate/', PersonaGenerateView.as_view(), name='persona_generate'),
    path('persona/latest/', PersonaLatestView.as_view(), name='persona_latest'),
    path('persona/history/', PersonaHistoryView.as_view(), name='persona_history'),
    path('recommendations/', SongRecommendationsView.as_view(), name='recommendations'),
    path('facts/', MusicFactsView.as_view(), name='music_facts'),
    path('codebase/query/', CodebaseQueryView.as_view(), name='codebase_query'),
    path('codebase/index/', CodebaseIndexView.as_view(), name='codebase_index'),
]
