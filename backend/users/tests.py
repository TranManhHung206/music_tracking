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


class Phase1AuthSecurityTests(TestCase):
    """Kiem thu bao mat OAuth state, exchange_code 1 lan, fail-closed /v1/me va is_staff."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.existing_user = User.objects.create_user(
            username="existing_victim", password="pw", is_staff=True
        )
        self.existing_profile = SpotifyProfile.objects.create(
            user=self.existing_user,
            spotify_id="victim_sp_id",
            display_name="Victim",
            encrypted_access_token=encrypt_token("acc"),
            encrypted_refresh_token=encrypt_token("ref"),
            token_expires_at=timezone.now() + timedelta(hours=1),
        )

    def _start_login_and_get_state(self):
        resp = self.client.get("/api/users/spotify/login/")
        self.assertIn(resp.status_code, (200, 302))
        if resp.status_code == 302:
            auth_url = resp["Location"]
        else:
            auth_url = resp.json()["auth_url"]
        from urllib.parse import urlparse, parse_qs
        state = parse_qs(urlparse(auth_url).query)["state"][0]
        return state

    def test_callback_rejects_invalid_state(self):
        resp = self.client.get("/api/users/spotify/callback/?code=testcode&state=bad_state_123")
        if resp.status_code == 302:
            self.assertIn("auth_error=", resp["Location"])
            self.assertNotIn("token=", resp["Location"])
        else:
            self.assertIn(resp.status_code, (400, 403))

    def test_callback_me_failure_does_not_fallback_to_existing_user(self):
        from unittest.mock import patch, MagicMock

        state = self._start_login_and_get_state()
        mock_me = MagicMock()
        mock_me.status_code = 500
        mock_me.text = "Spotify upstream failure"

        with patch("users.views.exchange_code_for_tokens", return_value={
            "access_token": "sp_acc",
            "refresh_token": "sp_ref",
            "expires_in": 3600,
        }), patch("requests.Session.get", return_value=mock_me):
            resp = self.client.get(f"/api/users/spotify/callback/?code=good_code&state={state}")

        if resp.status_code == 302:
            self.assertIn("auth_error=", resp["Location"])
            self.assertNotIn("exchange_code=", resp["Location"])
            self.assertNotIn("token=", resp["Location"])
        else:
            self.assertEqual(resp.status_code, 502)

    def test_exchange_code_one_time_flow_and_replay_rejected(self):
        from unittest.mock import patch, MagicMock
        from urllib.parse import urlparse, parse_qs

        state = self._start_login_and_get_state()
        mock_me = MagicMock()
        mock_me.status_code = 200
        mock_me.json.return_value = {
            "id": "new_oauth_sp_user",
            "display_name": "New OAuth Listener",
            "email": "new@example.com",
            "country": "VN",
            "images": [{"url": "https://example.com/avatar.jpg"}],
        }

        with patch("users.views.exchange_code_for_tokens", return_value={
            "access_token": "sp_acc_new",
            "refresh_token": "sp_ref_new",
            "expires_in": 3600,
        }), patch("requests.Session.get", return_value=mock_me):
            resp = self.client.get(
                f"/api/users/spotify/callback/?code=good_code&state={state}",
                HTTP_ACCEPT="text/html",
            )

        self.assertEqual(resp.status_code, 302)
        location = resp["Location"]
        self.assertNotIn("token=", location)
        self.assertIn("exchange_code=", location)
        exchange_code = parse_qs(urlparse(location).query)["exchange_code"][0]

        # Exchange code first time -> 200 with DRF token & user
        ex_resp = self.client.post(
            "/api/users/spotify/exchange/",
            {"exchange_code": exchange_code},
            format="json",
        )
        self.assertEqual(ex_resp.status_code, 200)
        ex_data = ex_resp.json()
        self.assertIn("token", ex_data)
        self.assertIn("user", ex_data)
        self.assertFalse(ex_data["user"]["is_staff"])

        # Replay same exchange_code -> rejected
        replay_ex = self.client.post(
            "/api/users/spotify/exchange/",
            {"exchange_code": exchange_code},
            format="json",
        )
        self.assertEqual(replay_ex.status_code, 400)

        # Replay same OAuth state -> rejected
        replay_cb = self.client.get(f"/api/users/spotify/callback/?code=good_code&state={state}")
        if replay_cb.status_code == 302:
            self.assertIn("auth_error=", replay_cb["Location"])
        else:
            self.assertEqual(replay_cb.status_code, 400)

    def test_profile_serializer_exposes_is_staff_and_hides_tokens(self):
        from users.serializers import SpotifyProfileSerializer

        data = SpotifyProfileSerializer(self.existing_profile).data
        self.assertTrue(data["is_staff"])
        self.assertNotIn("encrypted_access_token", data)
        self.assertNotIn("encrypted_refresh_token", data)

