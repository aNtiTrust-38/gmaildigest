"""
Custom exceptions for the authentication module.

This module defines exceptions that can be raised during OAuth authentication,
token storage, refresh, and revocation operations.
"""


class AuthError(Exception):
    """Base exception class for authentication errors."""
    
    def __init__(self, message: str = "Authentication error occurred"):
        self.message = message
        super().__init__(self.message)


class TokenNotFoundError(AuthError):
    """Raised when a token is not found for a given account."""
    
    def __init__(self, account: str = None):
        message = f"Token not found for account: {account}" if account else "Token not found"
        super().__init__(message)
        self.account = account


class TokenRefreshError(AuthError):
    """Raised when token refresh fails."""
    
    def __init__(self, message: str = "Failed to refresh token", original_error=None):
        super().__init__(message)
        self.original_error = original_error


class TokenRevocationError(AuthError):
    """Raised when token revocation fails."""
    
    def __init__(self, message: str = "Failed to revoke token", original_error=None):
        super().__init__(message)
        self.original_error = original_error


class TokenStorageError(AuthError):
    """Raised when there's an error storing or retrieving tokens from storage."""
    
    def __init__(self, message: str = "Token storage error", original_error=None):
        super().__init__(message)
        self.original_error = original_error


class EncryptionError(AuthError):
    """Raised when there's an error with token encryption or decryption."""
    
    def __init__(self, message: str = "Token encryption/decryption error", original_error=None):
        super().__init__(message)
        self.original_error = original_error


class AuthorizationFlowError(AuthError):
    """Raised when the OAuth authorization flow fails."""
    
    def __init__(self, message: str = "Authorization flow failed", original_error=None):
        super().__init__(message)
        self.original_error = original_error
