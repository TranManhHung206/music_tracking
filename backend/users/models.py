from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from users.services.encryption import encrypt_token, decrypt_token

class SpotifyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='spotify_profile')
    spotify_id = models.CharField(max_length=128, unique=True, db_index=True)
    display_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    avatar_url = models.URLField(max_length=512, blank=True, null=True)
    country = models.CharField(max_length=10, blank=True, null=True)
    timezone = models.CharField(max_length=64, default='Asia/Ho_Chi_Minh', blank=True)

    encrypted_access_token = models.TextField(blank=True, default='')
    encrypted_refresh_token = models.TextField(blank=True, default='')
    token_expires_at = models.DateTimeField(null=True, blank=True)

    is_sync_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_spotify_profile'
        indexes = [
            models.Index(fields=['spotify_id']),
            models.Index(fields=['is_sync_active', 'token_expires_at']),
        ]

    def __str__(self):
        return f"{self.display_name or self.spotify_id} ({self.user.username})"

    def get_access_token(self) -> str:
        """Giai ma va tra ve access token."""
        return decrypt_token(self.encrypted_access_token)

    def get_refresh_token(self) -> str:
        """Giai ma va tra ve refresh token."""
        return decrypt_token(self.encrypted_refresh_token)

    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int = 3600):
        """Ma hoa va luu access token, refresh token kem thoi diem het han."""
        self.encrypted_access_token = encrypt_token(access_token)
        if refresh_token:
            self.encrypted_refresh_token = encrypt_token(refresh_token)
        self.token_expires_at = timezone.now() + timedelta(seconds=expires_in)

    def is_token_expired(self, buffer_seconds: int = 300) -> bool:
        """Kiem tra xem token da het han hoac con duoi buffer_seconds khong."""
        if not self.token_expires_at:
            return True
        return timezone.now() >= (self.token_expires_at - timedelta(seconds=buffer_seconds))
