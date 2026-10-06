"""
Serializers cho app users.
San loc payload tra ve de bao ve tuyet doi cac truong token bi mat.
"""

from rest_framework import serializers
from .models import SpotifyProfile

class SpotifyProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SpotifyProfile
        fields = [
            'id',
            'username',
            'spotify_id',
            'display_name',
            'email',
            'avatar_url',
            'country',
            'is_sync_active',
            'last_synced_at',
            'created_at',
        ]
        read_only_fields = fields
