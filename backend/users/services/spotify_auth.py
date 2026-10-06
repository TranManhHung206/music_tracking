"""
Spotify OAuth & Accounts Service
Quan ly luong Authorization Code Flow, hoan doi token, refresh token va goi Spotify Profile API.
"""

import base64
import secrets
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_ME_URL = "https://api.spotify.com/v1/me"

REQUIRED_SCOPES = [
    "user-read-recently-played",
    "user-top-read",
    "user-read-private",
    "user-read-email",
]

def get_spotify_credentials() -> tuple[str, str, str]:
    """Lay va kiem tra thong tin xac thuc Spotify App tu settings."""
    client_id = getattr(settings, 'SPOTIFY_CLIENT_ID', '')
    client_secret = getattr(settings, 'SPOTIFY_CLIENT_SECRET', '')
    redirect_uri = getattr(settings, 'SPOTIFY_REDIRECT_URI', '')
    if not client_id or not client_secret:
        raise ImproperlyConfigured("SPOTIFY_CLIENT_ID va SPOTIFY_CLIENT_SECRET bat buoc phai co.")
    return client_id, client_secret, redirect_uri

def get_auth_header(client_id: str, client_secret: str) -> dict:
    """Tao Basic Authorization header cho request Spotify Token."""
    creds = f"{client_id}:{client_secret}".encode('utf-8')
    b64_creds = base64.b64encode(creds).decode('utf-8')
    return {
        "Authorization": f"Basic {b64_creds}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

def generate_spotify_auth_url(state: str = None) -> tuple[str, str]:
    """Tao Spotify Authorization URL kem ma state token chong CSRF."""
    client_id, _, redirect_uri = get_spotify_credentials()
    if not state:
        state = secrets.token_urlsafe(24)

    scope_str = " ".join(REQUIRED_SCOPES)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope_str,
        "state": state,
        "show_dialog": "true",
    }
    encoded_params = requests.compat.urlencode(params)
    auth_url = f"{SPOTIFY_AUTH_URL}?{encoded_params}"
    return auth_url, state

def exchange_code_for_tokens(code: str) -> dict:
    """Gui ma auth code de doi lay access_token va refresh_token tu Spotify."""
    client_id, client_secret, redirect_uri = get_spotify_credentials()
    headers = get_auth_header(client_id, client_secret)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers, timeout=10)
    if response.status_code != 200:
        raise ValueError(f"Spotify token exchange failed ({response.status_code}): {response.text}")
    return response.json()

def fetch_spotify_profile(access_token: str) -> dict:
    """Lay thong tin profile nguoi dung tu Spotify API /me."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(SPOTIFY_ME_URL, headers=headers, timeout=10)
    if response.status_code != 200:
        raise ValueError(f"Spotify profile fetch failed ({response.status_code}): {response.text}")
    return response.json()

def refresh_spotify_tokens(profile) -> str:
    """Su dung refresh_token de lay access_token moi khi token sap het han."""
    client_id, client_secret, _ = get_spotify_credentials()
    refresh_token = profile.get_refresh_token()
    if not refresh_token:
        raise ValueError("Profile khong co refresh token hop le.")

    headers = get_auth_header(client_id, client_secret)
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers, timeout=10)
    if response.status_code != 200:
        raise ValueError(f"Spotify refresh token failed ({response.status_code}): {response.text}")

    token_data = response.json()
    new_access_token = token_data.get("access_token")
    new_refresh_token = token_data.get("refresh_token", refresh_token)
    expires_in = token_data.get("expires_in", 3600)

    profile.set_tokens(new_access_token, new_refresh_token, expires_in)
    profile.save(update_fields=["encrypted_access_token", "encrypted_refresh_token", "token_expires_at", "updated_at"])
    return new_access_token

def get_valid_access_token(profile) -> str:
    """Kiem tra va tra ve access token hop le (tu dong refresh neu can)."""
    if profile.is_token_expired(buffer_seconds=300):
        return refresh_spotify_tokens(profile)
    return profile.get_access_token()
