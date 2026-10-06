"""
Data models cho ung dung AI Engine.
Luu tru ket qua phan tich tam ly am nhac (AI Music Persona) tu Groq / Gemini API.
"""

from django.db import models
from django.contrib.auth.models import User

class AIMusicPersona(models.Model):
    """Luu tru bao cao ca tinh am nhac va tam ly nghe nhac do AI sinh ra."""

    PERIOD_CHOICES = [
        ('weekly', 'Hàng tuần'),
        ('monthly', 'Hàng tháng'),
        ('all_time', 'Toàn thời gian'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_personas')
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='monthly')
    
    persona_title = models.CharField(max_length=255)
    tagline = models.CharField(max_length=500)
    vibe_summary = models.TextField()
    
    # mood_distribution vi du: {"energetic": 45, "melancholic": 30, "focused": 25}
    mood_distribution = models.JSONField(default=dict)
    
    recommended_listening_time = models.CharField(max_length=100, blank=True, null=True)
    ai_advice = models.TextField()
    
    provider_used = models.CharField(max_length=50, default='groq')
    model_name = models.CharField(max_length=100, default='openai/gpt-oss-120b')
    raw_ai_response = models.JSONField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_music_persona'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'period_type']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.persona_title} ({self.period_type})"
