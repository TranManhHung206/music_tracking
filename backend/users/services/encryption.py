"""
Token Encryption Service
Cung cap cac ham ma hoa va giai ma doi xung AES-256 (Fernet) cho Spotify tokens.
"""

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

def get_fernet_cipher() -> Fernet:
    """Khoi tao Fernet cipher tu FERNET_SECRET_KEY trong settings."""
    key = getattr(settings, 'FERNET_SECRET_KEY', None)
    if not key:
        raise ImproperlyConfigured("FERNET_SECRET_KEY chua duoc cau hinh trong settings.")
    if isinstance(key, str):
        key = key.encode('utf-8')
    return Fernet(key)

def encrypt_token(plain_token: str) -> str:
    """Ma hoa token sang chuoi cipher text an toan."""
    if not plain_token:
        return ""
    cipher = get_fernet_cipher()
    return cipher.encrypt(plain_token.encode('utf-8')).decode('utf-8')

def decrypt_token(cipher_token: str) -> str:
    """Giai ma cipher text ve token goc dang plaintext."""
    if not cipher_token:
        return ""
    cipher = get_fernet_cipher()
    return cipher.decrypt(cipher_token.encode('utf-8')).decode('utf-8')
