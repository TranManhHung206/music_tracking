"""
API Views cho ung dung AI Engine:
- POST /api/ai/persona/generate/
- GET  /api/ai/persona/latest/
- GET  /api/ai/persona/history/
- GET  /api/ai/recommendations/
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import AIMusicPersona
from .serializers import (
    AIMusicPersonaSerializer,
    GeneratePersonaRequestSerializer,
    MusicFactsResponseSerializer,
)
from .services import (
    generate_and_save_persona,
    get_song_recommendations,
    get_or_generate_music_facts,
)

class PersonaGenerateView(APIView):
    """API kich hoat tien trinh AI phan tich tam ly va ca tinh am nhac cua nguoi dung."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GeneratePersonaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        period_type = serializer.validated_data.get('period_type', 'monthly')

        persona_obj = generate_and_save_persona(request.user, period_type=period_type)
        response_serializer = AIMusicPersonaSerializer(persona_obj)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class PersonaLatestView(APIView):
    """API lay bao cao AI Music Persona moi nhat cua nguoi dung."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_type = request.query_params.get('period_type')
        qs = AIMusicPersona.objects.filter(user=request.user)
        if period_type:
            qs = qs.filter(period_type=period_type)

        latest_persona = qs.first()
        if not latest_persona:
            # Neu chua co bao cao, tu dong sinh bao cao dau tien
            period = period_type if period_type in ['weekly', 'monthly', 'all_time'] else 'monthly'
            latest_persona = generate_and_save_persona(request.user, period_type=period)

        serializer = AIMusicPersonaSerializer(latest_persona)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PersonaHistoryView(APIView):
    """API lay danh sach lich su cac bao cao Persona da tao."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        personas = AIMusicPersona.objects.filter(user=request.user)[:20]
        serializer = AIMusicPersonaSerializer(personas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class SongRecommendationsView(APIView):
    """API goi y bai hat co dac tinh am thanh tuong dong bang thuat toan KNN."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        track_id = request.query_params.get('track_id') or request.query_params.get('spotify_id')
        if not track_id:
            return Response(
                {"error": "Vui long truyen tham so track_id hoac spotify_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            top_k = min(max(int(request.query_params.get('top_k', 5)), 1), 20)
        except ValueError:
            top_k = 5

        try:
            result = get_song_recommendations(track_id, top_k=top_k)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

class MusicFactsView(APIView):
    """API lay danh sach su that am nhac do Aura Music Detective Agent truy vet."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'week')
        force_refresh_str = request.query_params.get('refresh', 'false').lower()
        force_refresh = force_refresh_str in ['true', '1', 'yes']

        result = get_or_generate_music_facts(
            user=request.user,
            period_key=period,
            force_refresh=force_refresh,
        )
        serializer = MusicFactsResponseSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)

