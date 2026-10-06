from django.contrib import admin
from .models import SpotifyProfile

@admin.register(SpotifyProfile)
class SpotifyProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'spotify_id', 'display_name', 'email', 'is_sync_active', 'token_expires_at', 'last_synced_at')
    list_filter = ('is_sync_active', 'created_at')
    search_fields = ('spotify_id', 'display_name', 'email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
