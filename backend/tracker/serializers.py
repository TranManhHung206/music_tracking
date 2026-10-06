"""
Serializers cho app tracker.
Tuan tu hoa du lieu Artist, Album, Track va ListeningHistory.
"""

from rest_framework import serializers
from .models import Artist, Album, Track, ListeningHistory

class ArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['spotify_id', 'name', 'genres', 'image_url']

class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = ['spotify_id', 'name', 'release_date', 'image_url']

class TrackSerializer(serializers.ModelSerializer):
    artists = ArtistSerializer(many=True, read_only=True)
    album = AlbumSerializer(read_only=True)

    class Meta:
        model = Track
        fields = [
            'spotify_id',
            'name',
            'duration_ms',
            'album',
            'artists',
            'danceability',
            'energy',
            'valence',
            'acousticness',
            'tempo',
            'features_synced',
        ]

class ListeningHistorySerializer(serializers.ModelSerializer):
    track = TrackSerializer(read_only=True)

    class Meta:
        model = ListeningHistory
        fields = [
            'id',
            'track',
            'played_at',
            'context_type',
            'created_at',
        ]
