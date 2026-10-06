"""
URL routes cho app analytics:
- summary/
- top-tracks/
- top-artists/
- radar/
- heatmap/
- bar-chart-race/
"""

from django.urls import path
from .views import (
    SummaryAnalyticsView,
    TopTracksAnalyticsView,
    TopArtistsAnalyticsView,
    RadarFeaturesAnalyticsView,
    HeatmapAnalyticsView,
    BarChartRaceAnalyticsView,
)

app_name = 'analytics'

urlpatterns = [
    path('summary/', SummaryAnalyticsView.as_view(), name='summary'),
    path('top-tracks/', TopTracksAnalyticsView.as_view(), name='top_tracks'),
    path('top-artists/', TopArtistsAnalyticsView.as_view(), name='top_artists'),
    path('radar/', RadarFeaturesAnalyticsView.as_view(), name='radar'),
    path('heatmap/', HeatmapAnalyticsView.as_view(), name='heatmap'),
    path('bar-chart-race/', BarChartRaceAnalyticsView.as_view(), name='bar_chart_race'),
]
