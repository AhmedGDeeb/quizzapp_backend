import secrets
import hashlib
from django.utils import timezone
from datetime import timedelta

def generate_verification_token():
    """Generate a secure random token for email verification"""
    return secrets.token_urlsafe(32)

def generate_reactivation_token():
    """Generate a secure random token for account reactivation"""
    return secrets.token_urlsafe(32)

def hash_token(token):
    """Hash token for secure storage (optional but recommended)"""
    return hashlib.sha256(token.encode()).hexdigest()