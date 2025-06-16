"""
Authentication module for Gmail Digest Assistant v2.

This module handles OAuth authentication with Google APIs, including token
storage, refresh, and revocation with support for multiple accounts.
"""
from gda.auth.manager import AuthManager
from gda.auth.store import TokenStore
from gda.auth.exceptions import (
    AuthError,
    TokenNotFoundError,
    TokenRefreshError,
    TokenRevocationError,
    TokenStorageError,
)

__all__ = [
    "AuthManager",
    "TokenStore",
    "AuthError",
    "TokenNotFoundError",
    "TokenRefreshError",
    "TokenRevocationError",
    "TokenStorageError",
]
