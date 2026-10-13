"""
Serializers cho app ai_engine.
Serialize model AIMusicPersona va validate tham so request cho AI endpoints.
"""

from rest_framework import serializers
from .models import AIMusicPersona

class AIMusicPersonaSerializer(serializers.ModelSerializer):
    """Serializer hien thi chi tiet bao cao AI Music Persona."""
    
    class Meta:
        model = AIMusicPersona
        fields = [
            'id',
            'period_type',
            'persona_title',
            'tagline',
            'vibe_summary',
            'mood_distribution',
            'recommended_listening_time',
            'ai_advice',
            'provider_used',
            'model_name',
            'created_at',
        ]
        read_only_fields = ['id', 'provider_used', 'model_name', 'created_at']

class GeneratePersonaRequestSerializer(serializers.Serializer):
    """Validate request body khi yeu cau sinh Persona moi."""
    period_type = serializers.ChoiceField(
        choices=['weekly', 'monthly', 'all_time'],
        default='monthly',
        required=False,
    )

class MusicFactItemSerializer(serializers.Serializer):
    """Serializer cho tung su that am nhac do Agent phat hien."""
    id = serializers.CharField()
    category = serializers.CharField()
    badge = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    metric_highlight = serializers.CharField()
    evidence = serializers.CharField(allow_blank=True, required=False)

class MusicFactsResponseSerializer(serializers.Serializer):
    """Serializer cho phan hoi tong the tu Music Detective Agent."""
    facts = MusicFactItemSerializer(many=True)
    agent_meta = serializers.DictField()
    period_key = serializers.CharField()
    period_label = serializers.CharField()

