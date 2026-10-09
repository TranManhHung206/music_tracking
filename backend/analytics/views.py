"""
API Views cho ung dung Analytics.
Cung cap cac endpoint thong ke nghe nhac toi uu cache Redis/In-Memory:
- /api/analytics/summary/
- /api/analytics/top-tracks/
- /api/analytics/top-artists/
- /api/analytics/radar/
- /api/analytics/heatmap/
- /api/analytics/bar-chart-race/
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .services import (
    get_time_range_bounds,
    get_cache_ttl_for_range,
    build_analytics_cache_key,
    get_or_set_cached_metric,
    get_listening_summary,
    get_top_tracks,
    get_top_artists,
    get_radar_features,
    get_listening_heatmap,
    get_bar_chart_race,
)

class SummaryAnalyticsView(APIView):
    """API thong ke tong quan so luot nghe, tong thoi luong va so nghe si/album doc nhat."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        time_range = request.query_params.get('time_range', '30d')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        start_dt, end_dt, range_key = get_time_range_bounds(time_range, start_date, end_date)
        cache_key = build_analytics_cache_key(request.user.id, 'summary', range_key)
        ttl = get_cache_ttl_for_range(range_key)

        def compute():
            data = get_listening_summary(request.user, start_dt, end_dt)
            data['time_range'] = range_key
            return data

        result = get_or_set_cached_metric(cache_key, ttl, compute)
        return Response(result, status=status.HTTP_200_OK)

class TopTracksAnalyticsView(APIView):
    """API lay danh sach Top bai hat nghe nhieu nhat."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        time_range = request.query_params.get('time_range', '30d')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            limit = min(max(int(request.query_params.get('limit', 10)), 1), 50)
        except ValueError:
            limit = 10

        start_dt, end_dt, range_key = get_time_range_bounds(time_range, start_date, end_date)
        cache_key = f"{build_analytics_cache_key(request.user.id, 'top_tracks', range_key)}:{limit}"
        ttl = get_cache_ttl_for_range(range_key)

        def compute():
            return {
                "time_range": range_key,
                "limit": limit,
                "tracks": get_top_tracks(request.user, start_dt, end_dt, limit=limit),
            }

        result = get_or_set_cached_metric(cache_key, ttl, compute)
        return Response(result, status=status.HTTP_200_OK)

class TopArtistsAnalyticsView(APIView):
    """API lay danh sach Top nghe si nghe nhieu nhat."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        time_range = request.query_params.get('time_range', '30d')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            limit = min(max(int(request.query_params.get('limit', 10)), 1), 50)
        except ValueError:
            limit = 10

        start_dt, end_dt, range_key = get_time_range_bounds(time_range, start_date, end_date)
        cache_key = f"{build_analytics_cache_key(request.user.id, 'top_artists', range_key)}:{limit}"
        ttl = get_cache_ttl_for_range(range_key)

        def compute():
            return {
                "time_range": range_key,
                "limit": limit,
                "artists": get_top_artists(request.user, start_dt, end_dt, limit=limit),
            }

        result = get_or_set_cached_metric(cache_key, ttl, compute)
        return Response(result, status=status.HTTP_200_OK)

class RadarFeaturesAnalyticsView(APIView):
    """API lay 5 dac tinh am thanh chuan hoa [0.0, 1.0] cho bieu do Radar."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        time_range = request.query_params.get('time_range', '30d')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        start_dt, end_dt, range_key = get_time_range_bounds(time_range, start_date, end_date)
        cache_key = build_analytics_cache_key(request.user.id, 'radar', range_key)
        ttl = get_cache_ttl_for_range(range_key)

        def compute():
            return get_radar_features(request.user, start_dt, end_dt, time_range_label=range_key)

        result = get_or_set_cached_metric(cache_key, ttl, compute)
        return Response(result, status=status.HTTP_200_OK)

class HeatmapAnalyticsView(APIView):
    """API lay ma tran mat do nghe nhac 7 ngay x 24 gio."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        time_range = request.query_params.get('time_range', '30d')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        start_dt, end_dt, range_key = get_time_range_bounds(time_range, start_date, end_date)
        cache_key = build_analytics_cache_key(request.user.id, 'heatmap', range_key)
        ttl = get_cache_ttl_for_range(range_key)

        def compute():
            return get_listening_heatmap(request.user, start_dt, end_dt, time_range_label=range_key)

        result = get_or_set_cached_metric(cache_key, ttl, compute)
        return Response(result, status=status.HTTP_200_OK)

class BarChartRaceAnalyticsView(APIView):
    """API lay chuoi thoi gian luy ke don dieu cua Top nghe si cho bieu do Bar Chart Race."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        time_range = request.query_params.get('time_range', '1y')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        try:
            top_n = min(max(int(request.query_params.get('top_n', 5)), 2), 10)
        except ValueError:
            top_n = 5

        start_dt, end_dt, range_key = get_time_range_bounds(time_range, start_date, end_date)
        cache_key = f"{build_analytics_cache_key(request.user.id, 'bar_chart_race', range_key)}:{top_n}"
        ttl = get_cache_ttl_for_range(range_key)

        def compute():
            return get_bar_chart_race(request.user, start_dt, end_dt, top_n=top_n)

        result = get_or_set_cached_metric(cache_key, ttl, compute)
        return Response(result, status=status.HTTP_200_OK)

class GenreDistributionView(APIView):
    """API lay ti le phan bo the loai am nhac (EDM, US-UK, V-Pop, v.v.)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        time_range = request.query_params.get('time_range', '30d')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        start_dt, end_dt, range_key = get_time_range_bounds(time_range, start_date, end_date)
        cache_key = build_analytics_cache_key(request.user.id, 'genres', range_key)
        ttl = get_cache_ttl_for_range(range_key)

        def compute():
            from .services.calculations import get_genre_distribution
            return get_genre_distribution(request.user, start_dt, end_dt)

        result = get_or_set_cached_metric(cache_key, ttl, compute)
        return Response(result, status=status.HTTP_200_OK)

class CalendarPeriodsListView(APIView):
    """API tra ve danh sach cac ky thoi gian Tu Hien Tai Ve Qua Khu (Tuan / Thang / Nam)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_type = request.query_params.get('period_type', 'week')
        try:
            limit = min(max(int(request.query_params.get('limit', 12)), 1), 52)
        except ValueError:
            limit = 12

        from .services.filters import get_calendar_periods
        periods = get_calendar_periods(request.user, period_type=period_type, limit=limit)
        return Response({
            "period_type": period_type,
            "periods": periods
        }, status=status.HTTP_200_OK)

