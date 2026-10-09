"""
Views cho app tracker.
Cung cap API kich hoat dong bo thu cong, truy van lich su nghe va trang thai auto-scrobble.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ListeningHistory
from .serializers import ListeningHistorySerializer
from .services.ingestion import sync_user_recently_played_pipeline

class ManualSyncView(APIView):
    """Kich hoat dong bo lich su nghe nhac Spotify ngay lap tuc cho user hien tai."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            result = sync_user_recently_played_pipeline(request.user)
            return Response(result, status=status.HTTP_200_OK)
        except RuntimeError as e:
            err_str = str(e)
            if "SPOTIFY_RATE_LIMIT" in err_str:
                parts = err_str.split(":")
                retry_after_str = parts[1] if len(parts) > 1 else "60"
                try:
                    retry_secs = int(retry_after_str)
                except ValueError:
                    retry_secs = 60

                minutes = round(retry_secs / 60, 1)
                hours = round(retry_secs / 3600, 1)
                time_desc = f"{hours} giờ" if hours >= 1.0 else f"{minutes} phút"

                return Response(
                    {
                        "error": f"Spotify API đang tạm giới hạn tần suất (Rate Limit do gửi request liên tục hồi sáng). Spotify yêu cầu chờ khoảng {time_desc}.",
                        "retry_after_seconds": retry_secs,
                        "time_desc": time_desc,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ListeningHistoryListView(APIView):
    """Lay danh sach 50 ban ghi nghe nhac gan nhat cua user hien tai."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        limit = min(int(request.GET.get('limit', 50)), 100)
        histories = (
            ListeningHistory.objects.filter(user=request.user)
            .select_related('track', 'track__album')
            .prefetch_related('track__artists')[:limit]
        )
        serializer = ListeningHistorySerializer(histories, many=True)
        return Response({
            "count": len(serializer.data),
            "results": serializer.data
        }, status=status.HTTP_200_OK)

class TrackerStatusView(APIView):
    """Lay trang thai Auto-Scrobbler cua nguoi dung."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, 'spotify_profile', None)
        total_scrobbles = ListeningHistory.objects.filter(user=request.user).count()

        return Response({
            "is_sync_active": profile.is_sync_active if profile else False,
            "last_synced_at": profile.last_synced_at if profile else None,
            "total_scrobbles": total_scrobbles,
        }, status=status.HTTP_200_OK)
