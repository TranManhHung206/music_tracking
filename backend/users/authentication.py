"""
Custom Authentication Class ho tro ca hai dinh dang Token va Bearer header.
"""

from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions

class BearerOrTokenAuthentication(TokenAuthentication):
    """
    Xac thuc nguoi dung qua HTTP Header Authorization.
    Chap nhan ca 'Authorization: Token <key>' lan 'Authorization: Bearer <key>'.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2:
            return None

        prefix, key = parts[0], parts[1]
        if prefix.lower() not in ['token', 'bearer']:
            return None

        return self.authenticate_credentials(key)
