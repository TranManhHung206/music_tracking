"""
Serializers cho app users.
San loc payload tra ve de bao ve tuyet doi cac truong token bi mat.
"""

from rest_framework import serializers
from .models import SpotifyProfile

class SpotifyProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    profile_image_url = serializers.CharField(source='avatar_url', read_only=True, allow_null=True)
    is_spotify_connected = serializers.SerializerMethodField()

    def get_is_spotify_connected(self, obj):
        return bool(obj.spotify_id and obj.encrypted_access_token)

    class Meta:
        model = SpotifyProfile
        fields = [
            'id',
            'username',
            'spotify_id',
            'display_name',
            'email',
            'avatar_url',
            'profile_image_url',
            'country',
            'is_spotify_connected',
            'is_sync_active',
            'last_synced_at',
            'created_at',
        ]
        read_only_fields = fields
