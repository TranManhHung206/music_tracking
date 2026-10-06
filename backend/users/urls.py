"""
URL routing cho app users.
"""

from django.urls import path
from .views import (
    SpotifyLoginView,
    SpotifyCallbackView,
    CurrentUserView,
    LogoutView,
    DisconnectSpotifyView,
)

urlpatterns = [
    path('spotify/login/', SpotifyLoginView.as_view(), name='spotify-login'),
    path('spotify/callback/', SpotifyCallbackView.as_view(), name='spotify-callback'),
    path('spotify/disconnect/', DisconnectSpotifyView.as_view(), name='spotify-disconnect'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
