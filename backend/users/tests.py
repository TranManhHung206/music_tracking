from datetime import timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from .models import SpotifyProfile
from .serializers import SpotifyProfileSerializer
from .services.encryption import encrypt_token, decrypt_token
from .services.spotify_auth import REQUIRED_SCOPES

class EncryptionServiceTest(TestCase):
    def test_fernet_roundtrip(self):
        plain_token = "BQC_sample_secret_spotify_token_12345"
        cipher_text = encrypt_token(plain_token)
        self.assertNotEqual(plain_token, cipher_text)
        decrypted = decrypt_token(cipher_text)
        self.assertEqual(plain_token, decrypted)

    def test_empty_token(self):
        self.assertEqual(encrypt_token(""), "")
        self.assertEqual(decrypt_token(""), "")

class SpotifyProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_spotify_user")
        self.profile = SpotifyProfile.objects.create(
            user=self.user,
            spotify_id="spot_12345",
            display_name="Test User",
            email="test@example.com"
        )
        self.profile.set_tokens("access_token_abc", "refresh_token_xyz", expires_in=3600)
        self.profile.save()

    def test_token_getters_and_setters(self):
        self.assertEqual(self.profile.get_access_token(), "access_token_abc")
        self.assertEqual(self.profile.get_refresh_token(), "refresh_token_xyz")
        # Raw database values must be encrypted
        self.assertNotEqual(self.profile.encrypted_access_token, "access_token_abc")
        self.assertNotEqual(self.profile.encrypted_refresh_token, "refresh_token_xyz")

    def test_token_expiry_check(self):
        # Currently valid (3600s in future)
        self.assertFalse(self.profile.is_token_expired(buffer_seconds=300))
        # Simulated expired
        self.profile.token_expires_at = timezone.now() - timedelta(minutes=10)
        self.profile.save()
        self.assertTrue(self.profile.is_token_expired(buffer_seconds=300))

class SpotifyAuthAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="api_user")
        self.profile = SpotifyProfile.objects.create(
            user=self.user,
            spotify_id="api_spot_999",
            display_name="API User",
            email="api@example.com"
        )
        self.profile.set_tokens("test_access", "test_refresh", 3600)
        self.profile.save()

    def test_spotify_login_endpoint(self):
        response = self.client.get('/api/users/spotify/login/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('auth_url', data)
        self.assertIn('state', data)
        for scope in REQUIRED_SCOPES:
            self.assertIn(scope, data['auth_url'])

    def test_current_user_unauthorized(self):
        response = self.client.get('/api/users/me/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_current_user_authorized_sanitized(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['spotify_id'], "api_spot_999")
        self.assertEqual(data['display_name'], "API User")
        # Ensure zero leakage
        self.assertNotIn('encrypted_access_token', data)
        self.assertNotIn('encrypted_refresh_token', data)
        self.assertNotIn('access_token', data)
        self.assertNotIn('refresh_token', data)

    def test_serializer_fields(self):
        serializer = SpotifyProfileSerializer(self.profile)
        data = serializer.data
        self.assertIn('spotify_id', data)
        self.assertIn('display_name', data)
        self.assertNotIn('encrypted_access_token', data)
        self.assertNotIn('encrypted_refresh_token', data)

class UserTimezoneMiddlewareTest(TestCase):
    def setUp(self):
        from django.test import RequestFactory
        from .middleware import UserTimezoneMiddleware
        self.factory = RequestFactory()
        self.middleware = UserTimezoneMiddleware(lambda req: timezone.get_current_timezone_name())

    def test_custom_valid_timezone_header(self):
        req = self.factory.get('/api/users/me/', HTTP_X_TIMEZONE='America/New_York')
        tz_result = self.middleware(req)
        self.assertEqual(tz_result, 'America/New_York')

    def test_vietnam_timezone_header(self):
        req = self.factory.get('/api/users/me/', HTTP_X_TIMEZONE='Asia/Ho_Chi_Minh')
        tz_result = self.middleware(req)
        self.assertEqual(tz_result, 'Asia/Ho_Chi_Minh')

    def test_invalid_timezone_fallback(self):
        req = self.factory.get('/api/users/me/', HTTP_X_TIMEZONE='Invalid/Not_A_Timezone_123')
        tz_result = self.middleware(req)
        self.assertIn(tz_result, ['Asia/Ho_Chi_Minh', 'UTC'])

