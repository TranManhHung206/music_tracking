"""
URL routing cho app tracker.
"""

from django.urls import path
from .views import (
    ManualSyncView,
    ListeningHistoryListView,
    TrackerStatusView,
)

urlpatterns = [
    path('sync/', ManualSyncView.as_view(), name='tracker-sync'),
    path('history/', ListeningHistoryListView.as_view(), name='tracker-history'),
    path('status/', TrackerStatusView.as_view(), name='tracker-status'),
]
