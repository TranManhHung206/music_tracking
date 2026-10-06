from django.contrib import admin
from .models import Artist, Album, Track, ListeningHistory

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name', 'spotify_id')
    search_fields = ('name', 'spotify_id')

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('name', 'spotify_id', 'release_date')
    search_fields = ('name', 'spotify_id')

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ('name', 'spotify_id', 'duration_ms', 'features_synced', 'danceability', 'energy', 'valence')
    list_filter = ('features_synced',)
    search_fields = ('name', 'spotify_id')

@admin.register(ListeningHistory)
class ListeningHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'track', 'played_at', 'context_type', 'created_at')
    list_filter = ('context_type', 'played_at')
    search_fields = ('user__username', 'track__name', 'track__spotify_id')
