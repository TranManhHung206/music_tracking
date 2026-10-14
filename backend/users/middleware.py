"""
User Timezone Middleware.
Tu dong nhan dien va kich hoat mui gio nguoi dung (Dynamic Timezone Activation) tren tung HTTP request.
Uu tien: Header 'X-Timezone' tu trinh duyet -> Profile user trong DB -> settings.TIME_ZONE.
"""

import zoneinfo
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class UserTimezoneMiddleware:
    """Middleware quan ly va kich hoat mui gio dong cho request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = None

        # 1. Uu tien header tu Client trinh duyet
        client_tz = request.headers.get('X-Timezone')
        if client_tz and client_tz.strip():
            tz_name = client_tz.strip()

        # 2. Uu tien tiep theo tu Query param
        if not tz_name:
            param_tz = request.GET.get('timezone')
            if param_tz and param_tz.strip():
                tz_name = param_tz.strip()

        # 3. Uu tien tu User SpotifyProfile trong DB neu da xac thuc
        if not tz_name and getattr(request, 'user', None) and request.user.is_authenticated:
            profile = getattr(request.user, 'spotify_profile', None)
            if profile and getattr(profile, 'timezone', None):
                tz_name = profile.timezone

        # 4. Fallback ve mac dinh he thong
        if not tz_name:
            tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Ho_Chi_Minh')

        # Kich hoat mui gio an toan voi phong ve ZoneInfoNotFoundError
        active_tz = None
        try:
            active_tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            try:
                active_tz = zoneinfo.ZoneInfo(getattr(settings, 'TIME_ZONE', 'Asia/Ho_Chi_Minh'))
                tz_name = getattr(settings, 'TIME_ZONE', 'Asia/Ho_Chi_Minh')
            except Exception:
                active_tz = zoneinfo.ZoneInfo('UTC')
                tz_name = 'UTC'

        timezone.activate(active_tz)
        request.timezone_name = tz_name

        try:
            response = self.get_response(request)
        finally:
            timezone.deactivate()

        return response
