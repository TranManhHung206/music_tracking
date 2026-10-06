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

        if error:
            return Response({"error": f"Spotify tra ve loi: {error}"}, status=status.HTTP_400_BAD_REQUEST)
        if not code:
            return Response({"error": "Thieu tham so code tu Spotify."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_data = exchange_code_for_tokens(code)
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 3600)

            spotify_user_data = fetch_spotify_profile(access_token)
            spotify_id = spotify_user_data.get('id')
            display_name = spotify_user_data.get('display_name') or spotify_id
            email = spotify_user_data.get('email')
            country = spotify_user_data.get('country')
            images = spotify_user_data.get('images', [])
            avatar_url = images[0].get('url') if images else None

            # Dong bo User he thong
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

            login(request, user)

            # Neu request den tu trinh duyet thi chuyen huong ve Frontend
            redirect_to_frontend = request.GET.get('redirect', 'true').lower() == 'true'
            if 'text/html' in request.headers.get('Accept', '') and redirect_to_frontend:
                return redirect("http://localhost:5173/?auth_success=true")

            serializer = SpotifyProfileSerializer(profile)
            return Response({
                "message": "Xac thuc Spotify thanh cong.",
                "user": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
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
