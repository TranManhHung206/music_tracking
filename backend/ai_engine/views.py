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
    CodebaseQueryRequestSerializer,
    CodebaseQueryResponseSerializer,
)
from .services import (
    generate_and_save_persona,
    get_song_recommendations,
    get_or_generate_music_facts,
    get_rag_service,
)
from .services.rag.retrieval.cascade import PipelineMode

from django.core.cache import cache

class PersonaGenerateView(APIView):
    """API kich hoat tien trinh AI phan tich tam ly va ca tinh am nhac cua nguoi dung."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Anti-spam cooldown 15 giay cho nguoi dung
        cooldown_key = f"user_persona_cooldown:{request.user.id}"
        if cache.get(cooldown_key):
            latest = AIMusicPersona.objects.filter(user=request.user).first()
            if latest:
                return Response(AIMusicPersonaSerializer(latest).data, status=status.HTTP_200_OK)
        cache.set(cooldown_key, True, timeout=15)

        serializer = GeneratePersonaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        period_type = serializer.validated_data.get('period_type', 'monthly')

        persona_obj = generate_and_save_persona(request.user, period_type=period_type)
        response_serializer = AIMusicPersonaSerializer(persona_obj)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

class PersonaLatestView(APIView):
    """API lay bao cao AI Music Persona moi nhat cua nguoi dung (chi doc du lieu san co, khong tu dong goi AI)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period_type = request.query_params.get('period_type')
        qs = AIMusicPersona.objects.filter(user=request.user)
        if period_type:
            qs = qs.filter(period_type=period_type)

        latest_persona = qs.first()
        if not latest_persona:
            # Tra ve JSON rong de giao dien hien thi the moi goi nguoi dung bam nut thu cong
            return Response({}, status=status.HTTP_200_OK)

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
        trigger_str = request.query_params.get('trigger', 'false').lower()
        manual_trigger = trigger_str in ['true', '1', 'yes'] or force_refresh

        result = get_or_generate_music_facts(
            user=request.user,
            period_key=period,
            force_refresh=force_refresh,
            allow_ai_generation=manual_trigger,
        )
        serializer = MusicFactsResponseSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CodebaseQueryView(APIView):
    """API hoi dap thong tin codebase va tai lieu du an qua he thong RAG."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CodebaseQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query_text = serializer.validated_data['query']
        mode_str = serializer.validated_data.get('mode', 'full_cascade')
        top_k = serializer.validated_data.get('top_k', 5)
        use_cache = serializer.validated_data.get('use_cache', True)

        try:
            mode_enum = PipelineMode(mode_str)
        except ValueError:
            mode_enum = PipelineMode.FULL_CASCADE

        rag_service = get_rag_service()
        response_obj = rag_service.query(
            query_text=query_text,
            mode=mode_enum,
            final_k=top_k,
            use_cache=use_cache,
        )

        res_serializer = CodebaseQueryResponseSerializer(response_obj.model_dump())
        return Response(res_serializer.data, status=status.HTTP_200_OK)


class CodebaseIndexView(APIView):
    """API quan tri danh chi muc (re-index) toan bo ma nguon va tai lieu."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        rag_service = get_rag_service()
        stats = rag_service.index_codebase(force=True)
        return Response(stats, status=status.HTTP_200_OK)


