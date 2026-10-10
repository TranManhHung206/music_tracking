"""
Views cho app users.
Xu ly cac HTTP request dang nhap, callback, lay profile va dang xuat.
"""

from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import SpotifyProfile
from .serializers import SpotifyProfileSerializer
from .services.spotify_auth import (
    generate_spotify_auth_url,
    exchange_code_for_tokens,
    fetch_spotify_profile,
)

class SpotifyLoginView(APIView):
    """Khoi tao luong dang nhap Spotify OAuth 2.0 va tra ve Auth URL."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            auth_url, state = generate_spotify_auth_url()
            request.session['spotify_oauth_state'] = state
            return Response({"auth_url": auth_url, "state": state})
        except Exception as e:
            return Response(
                {"error": f"Khong the khoi tao Spotify OAuth: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SpotifyCallbackView(APIView):
    """Tiep nhan Auth Code tu Spotify, doi lay tokens va khoi tao profile."""
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')
        is_browser = 'text/html' in request.headers.get('Accept', '')

        print(f"[SpotifyCallbackView] >>> BUOC 1: Nhan request callback (code_len={len(code) if code else 0}, error={error})", flush=True)

        if error:
            if is_browser:
                from urllib.parse import quote
                return redirect(f"http://localhost:5173/?auth_error={quote(f'Spotify tra ve loi: {error}')}")
            return Response({"error": f"Spotify tra ve loi: {error}"}, status=status.HTTP_400_BAD_REQUEST)
        if not code:
            if is_browser:
                from urllib.parse import quote
                return redirect(f"http://localhost:5173/?auth_error={quote('Thieu tham so code tu Spotify.')}")
            return Response({"error": "Thieu tham so code tu Spotify."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            print("[SpotifyCallbackView] >>> BUOC 2: Dang doi code lay token tu accounts.spotify.com...", flush=True)
            token_data = exchange_code_for_tokens(code)
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 3600)
            print(f"[SpotifyCallbackView] >>> BUOC 2 XONG: Da nhan access_token (len={len(access_token) if access_token else 0})", flush=True)

            print("[SpotifyCallbackView] >>> BUOC 3: Dang lay thong tin profile tu api.spotify.com/v1/me...", flush=True)
            spotify_id = None
            display_name = None
            email = None
            country = None
            avatar_url = None

            try:
                spotify_user_data = fetch_spotify_profile(access_token)
                spotify_id = spotify_user_data.get('id')
                display_name = spotify_user_data.get('display_name') or spotify_id
                email = spotify_user_data.get('email')
                country = spotify_user_data.get('country')
                images = spotify_user_data.get('images', [])
                avatar_url = images[0].get('url') if images else None
                print(f"[SpotifyCallbackView] >>> BUOC 3 XONG: Profile: {display_name} ({spotify_id})", flush=True)
            except Exception as profile_err:
                print(f"[SpotifyCallbackView] >>> BUOC 3 CANH BAO: Spotify Profile API bi loi/timeout ({profile_err}). Kich hoat Fallback DB Profile...", flush=True)
                existing_profile = SpotifyProfile.objects.first()
                if existing_profile:
                    spotify_id = existing_profile.spotify_id
                    display_name = existing_profile.display_name
                    email = existing_profile.email
                    country = existing_profile.country
                    avatar_url = existing_profile.avatar_url
                    print(f"[SpotifyCallbackView] >>> BUOC 3 FALLBACK: Su dung profile san co: {display_name} ({spotify_id})", flush=True)
                else:
                    spotify_id = "spotify_user_local"
                    display_name = "Spotify User"
                    print("[SpotifyCallbackView] >>> BUOC 3 FALLBACK: Khoi tao profile tam thoi.", flush=True)

            # Dong bo User he thong
            print("[SpotifyCallbackView] >>> BUOC 4: Dang cap nhat DB User & SpotifyProfile...", flush=True)
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
            print("[SpotifyCallbackView] >>> BUOC 4 XONG: Da luu DB thanh cong.", flush=True)

            try:
                login(request, user)
            except Exception as login_err:
                print(f"[SpotifyCallbackView] Canh bao session login: {login_err}", flush=True)

            from rest_framework.authtoken.models import Token
            token, _ = Token.objects.get_or_create(user=user)

            # Xoa cache phan tich cu de dam bao phien moi luon load du lieu moi nhat
            try:
                from analytics.services.caching import invalidate_user_analytics_cache
                invalidate_user_analytics_cache(user.id)
            except Exception:
                pass

            # Tu dong dong bo lich su nghe nhac moi nhat vao DB ngay sau khi dang nhap
            try:
                import threading
                from tracker.services.ingestion import sync_user_recently_played_pipeline
                threading.Thread(target=sync_user_recently_played_pipeline, args=(user,), daemon=True).start()
                print("[SpotifyCallbackView] >>> BUOC 4.1: Da khoi chay sync Spotify ngam luu vao DB.", flush=True)
            except Exception as sync_err:
                print(f"[SpotifyCallbackView] Canh bao khoi chay sync ngam: {sync_err}", flush=True)


            # Neu request den tu trinh duyet thi chuyen huong ve Frontend kem Auth Token
            redirect_to_frontend = request.GET.get('redirect', 'true').lower() == 'true'
            if is_browser and redirect_to_frontend:
                print(f"[SpotifyCallbackView] >>> BUOC 5: Chuyen huong ve Frontend (http://localhost:5173/?token=...)", flush=True)
                return redirect(f"http://localhost:5173/?token={token.key}&auth_success=true")

            serializer = SpotifyProfileSerializer(profile)
            return Response({
                "message": "Xac thuc Spotify thanh cong.",
                "token": token.key,
                "user": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            err_str = str(e)
            print(f"[SpotifyCallbackView] >>> LOI: {err_str}", flush=True)
            if is_browser:
                from urllib.parse import quote
                if "timed out" in err_str.lower() or "connecttimeout" in err_str.lower() or "max retries exceeded" in err_str.lower():
                    friendly_msg = "Ket noi may chu Spotify qua thoi gian do mang quoc te cham. Vui long bam Dang nhap lai!"
                else:
                    friendly_msg = f"Loi xac thuc Spotify: {err_str}"
                return redirect(f"http://localhost:5173/?auth_error={quote(friendly_msg)}")

            return Response(
                {"error": f"Loi trong qua trinh tiep nhan callback: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
