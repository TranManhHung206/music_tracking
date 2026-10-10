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
    TopAlbumsAnalyticsView,
    RadarFeaturesAnalyticsView,
    HeatmapAnalyticsView,
    BarChartRaceAnalyticsView,
    WeeklyComparisonAnalyticsView,
    GenreDistributionView,
    CalendarPeriodsListView,
)

app_name = 'analytics'

urlpatterns = [
    path('summary/', SummaryAnalyticsView.as_view(), name='summary'),
    path('top-tracks/', TopTracksAnalyticsView.as_view(), name='top_tracks'),
    path('top-artists/', TopArtistsAnalyticsView.as_view(), name='top_artists'),
    path('top-albums/', TopAlbumsAnalyticsView.as_view(), name='top_albums'),
    path('radar/', RadarFeaturesAnalyticsView.as_view(), name='radar'),
    path('heatmap/', HeatmapAnalyticsView.as_view(), name='heatmap'),
    path('bar-chart-race/', BarChartRaceAnalyticsView.as_view(), name='bar_chart_race'),
    path('weekly-comparison/', WeeklyComparisonAnalyticsView.as_view(), name='weekly_comparison'),
    path('genres/', GenreDistributionView.as_view(), name='genres'),
    path('periods/', CalendarPeriodsListView.as_view(), name='periods'),
]
