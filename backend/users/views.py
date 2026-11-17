"""
Views cho app users.
Xu ly cac HTTP request dang nhap, callback (kem xac thuc state va exchange_code), lay profile va dang xuat.
"""

import logging
import secrets
from urllib.parse import quote, urlparse

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SpotifyProfile
from .serializers import SpotifyProfileSerializer
from .services.spotify_auth import (
    generate_spotify_auth_url,
    exchange_code_for_tokens,
    fetch_spotify_profile,
)

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL = 600
OAUTH_EXCHANGE_TTL = 60


def _get_safe_frontend_url() -> str:
    """Lay URL Frontend hop le da duoc kiem duyet qua allowlist."""
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
    allowed = getattr(settings, 'ALLOWED_FRONTEND_ORIGINS', [base])
    parsed = urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ''
    if origin and origin in allowed:
        return base
    return allowed[0].rstrip('/') if allowed else 'http://localhost:5173'


def _consume_oauth_state(request, state: str | None) -> bool:
    """Xac thuc va tieu huy state token 1 lan (ho tro ca Cache lan Session)."""
    if not state:
        return False

    cache_key = f"spotify_oauth_state:{state}"
    session_state = request.session.pop('spotify_oauth_state', None)
    cached_valid = cache.get(cache_key)
    if cached_valid:
        cache.delete(cache_key)
        return True

    if session_state and secrets.compare_digest(str(session_state), str(state)):
        return True

    return False


class SpotifyLoginView(APIView):
    """Khoi tao luong dang nhap Spotify OAuth 2.0 va tra ve Auth URL kem state."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            auth_url, state = generate_spotify_auth_url()
            request.session['spotify_oauth_state'] = state
            cache.set(f"spotify_oauth_state:{state}", True, timeout=OAUTH_STATE_TTL)
            return Response({"auth_url": auth_url, "state": state})
        except Exception as e:
            return Response(
                {"error": f"Khong the khoi tao Spotify OAuth: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SpotifyCallbackView(APIView):
    """Tiep nhan Auth Code tu Spotify, xac thuc state, doi token va cap one-time exchange_code."""
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        is_browser = 'text/html' in request.headers.get('Accept', '')
        frontend_url = _get_safe_frontend_url()

        if error:
            if is_browser:
                return redirect(f"{frontend_url}/?auth_error={quote(f'Spotify tra ve loi: {error}')}")
            return Response({"error": f"Spotify tra ve loi: {error}"}, status=status.HTTP_400_BAD_REQUEST)

        if not _consume_oauth_state(request, state):
            msg = "Phien xac thuc Spotify khong hop le hoac da het han (State mismatch). Vui long dang nhap lai."
            if is_browser:
                return redirect(f"{frontend_url}/?auth_error={quote(msg)}")
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

        if not code:
            msg = "Thieu tham so code tu Spotify."
            if is_browser:
                return redirect(f"{frontend_url}/?auth_error={quote(msg)}")
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_data = exchange_code_for_tokens(code)
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 3600)

            try:
                spotify_user_data = fetch_spotify_profile(access_token)
            except Exception as profile_err:
                logger.warning("Spotify /v1/me profile lookup failed during OAuth callback: %s", profile_err)
                fail_msg = "Khong the xac minh danh tinh tai khoan Spotify. Vui long thu dang nhap lai."
                if is_browser:
                    return redirect(f"{frontend_url}/?auth_error={quote(fail_msg)}")
                return Response({"error": fail_msg}, status=status.HTTP_502_BAD_GATEWAY)

            spotify_id = spotify_user_data.get('id')
            if not spotify_id:
                fail_msg = "Spotify khong tra ve ma dinh danh tai khoan hop le."
                if is_browser:
                    return redirect(f"{frontend_url}/?auth_error={quote(fail_msg)}")
                return Response({"error": fail_msg}, status=status.HTTP_502_BAD_GATEWAY)

            display_name = spotify_user_data.get('display_name') or spotify_id
            email = spotify_user_data.get('email')
            country = spotify_user_data.get('country')
            images = spotify_user_data.get('images', [])
            avatar_url = images[0].get('url') if images else None

            username = f"spotify_{spotify_id}"
            user, _ = User.objects.get_or_create(username=username, defaults={'email': email or ''})

            profile, _ = SpotifyProfile.objects.get_or_create(
                spotify_id=spotify_id,
                defaults={'user': user}
            )
            profile.user = user
            profile.display_name = display_name
            profile.email = email
            profile.avatar_url = avatar_url
            profile.country = country
            profile.is_sync_active = True
            profile.set_tokens(access_token, refresh_token, expires_in)
            profile.save()

            try:
                login(request, user)
            except Exception as login_err:
                logger.warning("Session login warning: %s", login_err)

            token, _ = Token.objects.get_or_create(user=user)

            try:
                from analytics.services.caching import invalidate_user_analytics_cache
                invalidate_user_analytics_cache(user.id)
            except Exception:
                pass

            try:
                import threading
                from tracker.services.ingestion import sync_user_recently_played_pipeline
                threading.Thread(target=sync_user_recently_played_pipeline, args=(user,), daemon=True).start()
            except Exception as sync_err:
                logger.warning("Background sync start warning: %s", sync_err)

            redirect_to_frontend = request.GET.get('redirect', 'true').lower() == 'true'
            if is_browser and redirect_to_frontend:
                exchange_code = secrets.token_urlsafe(32)
                cache.set(
                    f"oauth_exchange:{exchange_code}",
                    {"token": token.key, "user_id": user.id},
                    timeout=OAUTH_EXCHANGE_TTL,
                )
                return redirect(f"{frontend_url}/?exchange_code={exchange_code}&auth_success=true")

            serializer = SpotifyProfileSerializer(profile)
            return Response({
                "message": "Xac thuc Spotify thanh cong.",
                "token": token.key,
                "user": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            err_str = str(e)
            logger.error("Spotify callback exception: %s", err_str)
            if is_browser:
                if "timed out" in err_str.lower() or "connecttimeout" in err_str.lower() or "max retries exceeded" in err_str.lower():
                    friendly_msg = "Ket noi may chu Spotify qua thoi gian do mang quoc te cham. Vui long bam Dang nhap lai!"
                else:
                    friendly_msg = "Loi xac thuc Spotify. Vui long thu lai."
                return redirect(f"{frontend_url}/?auth_error={quote(friendly_msg)}")

            return Response(
                {"error": f"Loi trong qua trinh tiep nhan callback: {err_str}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SpotifyExchangeCodeView(APIView):
    """Doi one-time exchange_code lay DRF auth token va thong tin user."""
    permission_classes = [AllowAny]

    def post(self, request):
        exchange_code = (request.data.get('exchange_code') or '').strip()
        if not exchange_code:
            return Response(
                {"error": "Thieu ma trao doi exchange_code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f"oauth_exchange:{exchange_code}"
        payload = cache.get(cache_key)
        if not payload or not isinstance(payload, dict):
            return Response(
                {"error": "Ma trao doi khong hop le hoac da het han."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Tieu huy ngay lap tuc de bao dam chi dung 1 lan
        cache.delete(cache_key)

        user_id = payload.get('user_id')
        token_key = payload.get('token')
        if not user_id or not token_key:
            return Response(
                {"error": "Du lieu trao doi khong hop le."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = SpotifyProfile.objects.select_related('user').get(user_id=user_id)
        except SpotifyProfile.DoesNotExist:
            return Response(
                {"error": "Khong tim thay ho so nguoi dung."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SpotifyProfileSerializer(profile)
        return Response({
            "token": token_key,
            "user": serializer.data,
        }, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    """Tra ve thong tin nguoi dung dang dang nhap hien tai."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.spotify_profile
            serializer = SpotifyProfileSerializer(profile)
            return Response(serializer.data)
        except SpotifyProfile.DoesNotExist:
            return Response(
                {"detail": "Tai khoan chua lien ket voi Spotify Profile."},
                status=status.HTTP_404_NOT_FOUND
            )


class LogoutView(APIView):
    """Dang xuat va xoa phien lam viec."""
    permission_classes = [AllowAny]

    def post(self, request):
        if request.user and request.user.is_authenticated and hasattr(request.user, 'auth_token'):
            try:
                request.user.auth_token.delete()
            except Exception:
                pass
        logout(request)
        return Response({"message": "Dang xuat thanh cong."}, status=status.HTTP_200_OK)


class DisconnectSpotifyView(APIView):
    """Ngat ket noi va xoa token Spotify cua nguoi dung."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = request.user.spotify_profile
            profile.is_sync_active = False
            profile.encrypted_access_token = ""
            profile.encrypted_refresh_token = ""
            profile.save(update_fields=['is_sync_active', 'encrypted_access_token', 'encrypted_refresh_token', 'updated_at'])
            return Response({"message": "Da ngat ket noi tai khoan Spotify thanh cong."})
        except SpotifyProfile.DoesNotExist:
            return Response(
                {"detail": "Khong tim thay profile Spotify."},
                status=status.HTTP_404_NOT_FOUND
            )
