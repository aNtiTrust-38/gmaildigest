"""
Authentication manager for Gmail Digest Assistant v2.

This module provides the AuthManager class that handles OAuth authentication
with Google APIs, including persistent token storage, automatic refresh with
retry/backoff logic, and a user-friendly authorization flow.
"""
import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable

import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from gda.auth.store import TokenStore
from gda.auth.exceptions import (
    AuthError,
    TokenNotFoundError,
    TokenRefreshError,
    TokenRevocationError,
    TokenStorageError,
    AuthorizationFlowError,
)

# Configure logger
logger = logging.getLogger(__name__)


class AuthManager:
    """
    Manages OAuth authentication with Google APIs.
    
    This class handles the OAuth flow, token storage, automatic refresh with
    retry/backoff logic, and user-friendly authorization. It uses TokenStore
    for persistent token storage with optional encryption.
    """
    
    def __init__(self, auth_settings):
        """
        Initialize the authentication manager.
        
        Args:
            auth_settings: Authentication settings from config
        """
        self.settings = auth_settings
        self.credentials_path = Path(auth_settings.credentials_path)
        
        # Initialize token store
        encryption_key = None
        if auth_settings.token_encryption_key:
            encryption_key = auth_settings.token_encryption_key.get_secret_value()
        
        self.token_store = TokenStore(
            db_path=auth_settings.token_db_path,
            encryption_key=encryption_key,
            auto_create=True,
        )
        
        # Background tasks
        self._refresh_tasks = {}
        
        logger.info(f"Initialized AuthManager with credentials at {self.credentials_path}")
    
    async def get_credentials(self, email: Optional[str] = None) -> Credentials:
        """
        Get valid credentials for an account.
        
        This method tries to load credentials from the token store. If the credentials
        are expired, it attempts to refresh them. If no valid credentials are found,
        it initiates a new OAuth flow.
        
        Args:
            email: Email address of the account (optional, uses default if not provided)
            
        Returns:
            Valid OAuth credentials
            
        Raises:
            AuthError: If authentication fails
        """
        # Use default email if not provided
        if not email:
            # Try to get the default email from client secrets
            email = await self._get_default_email()
        
        try:
            # Try to load credentials from token store
            token_data = await asyncio.to_thread(self.token_store.get_token, email)
            credentials = self._token_data_to_credentials(token_data)
            
            # Check if credentials are expired and need refresh
            if not credentials.valid:
                if credentials.expired and credentials.refresh_token:
                    # Refresh the token
                    credentials = await self._refresh_credentials(email, credentials)
                else:
                    # No refresh token or other issue, need new authorization
                    credentials = await self._run_auth_flow(email)
            
            # Schedule background refresh task if not already running
            self._ensure_refresh_task(email, credentials)
            
            return credentials
        
        except TokenNotFoundError:
            # No token found, run auth flow
            logger.info(f"No token found for {email}, initiating OAuth flow")
            return await self._run_auth_flow(email)
        
        except Exception as e:
            logger.error(f"Error getting credentials for {email}: {e}", exc_info=True)
            raise AuthError(f"Failed to get credentials: {e}")
    
    async def _refresh_credentials(
        self, email: str, credentials: Credentials, force: bool = False
    ) -> Credentials:
        """
        Refresh OAuth credentials with retry and backoff logic.
        
        Args:
            email: Email address of the account
            credentials: Credentials to refresh
            force: Whether to force refresh even if not expired
            
        Returns:
            Refreshed credentials
            
        Raises:
            TokenRefreshError: If refresh fails after all retries
        """
        if not credentials.refresh_token:
            logger.warning(f"No refresh token for {email}, cannot refresh")
            raise TokenRefreshError("No refresh token available")
        
        if not force and not credentials.expired:
            logger.debug(f"Credentials for {email} are still valid, skipping refresh")
            return credentials
        
        # Implement retry with exponential backoff
        max_retries = self.settings.max_refresh_retries
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Refreshing token for {email} (attempt {attempt+1}/{max_retries})")
                
                # Use Request object to refresh the token
                request = Request()
                
                # Run the refresh in a thread to avoid blocking
                await asyncio.to_thread(credentials.refresh, request)
                
                # Update token in storage
                await self._store_credentials(email, credentials)
                
                logger.info(f"Successfully refreshed token for {email}")
                return credentials
            
            except google.auth.exceptions.RefreshError as e:
                logger.warning(
                    f"Token refresh failed for {email} (attempt {attempt+1}/{max_retries}): {e}"
                )
                
                if attempt < max_retries - 1:
                    # Calculate backoff time with jitter
                    backoff_seconds = (2 ** attempt) + random.uniform(0, 1)
                    logger.debug(f"Retrying in {backoff_seconds:.2f} seconds")
                    await asyncio.sleep(backoff_seconds)
                else:
                    # All retries failed
                    logger.error(f"Token refresh failed for {email} after {max_retries} attempts")
                    raise TokenRefreshError(f"Failed to refresh token after {max_retries} attempts", e)
            
            except Exception as e:
                logger.error(f"Unexpected error refreshing token for {email}: {e}", exc_info=True)
                raise TokenRefreshError(f"Unexpected error refreshing token: {e}", e)
    
    async def _run_auth_flow(self, email: Optional[str] = None) -> Credentials:
        """
        Run the OAuth authorization flow.
        
        This method launches a browser window for the user to authorize the application.
        
        Args:
            email: Email address to use for the flow (optional)
            
        Returns:
            New OAuth credentials
            
        Raises:
            AuthorizationFlowError: If the authorization flow fails
        """
        try:
            logger.info("Starting OAuth authorization flow")
            
            # Check if credentials file exists
            if not self.credentials_path.exists():
                raise AuthorizationFlowError(
                    f"Credentials file not found at {self.credentials_path}"
                )
            
            # Run the OAuth flow in a thread to avoid blocking
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path), self.settings.scopes
            )
            
            # If email is provided, use it for login_hint
            if email:
                flow.oauth2session.redirect_uri = "http://localhost:0"
                flow.oauth2session.login_hint = email
            
            # Run the flow in a thread
            credentials = await asyncio.to_thread(
                flow.run_local_server, port=0, prompt="consent"
            )
            
            # Get email from credentials if not provided
            if not email:
                user_info = await self._get_user_info(credentials)
                email = user_info.get("email")
                
                if not email:
                    logger.warning("Could not determine email from OAuth flow")
                    email = "default@gmail.com"
            
            # Store the credentials
            await self._store_credentials(email, credentials)
            
            logger.info(f"Successfully completed OAuth flow for {email}")
            return credentials
        
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}", exc_info=True)
            raise AuthorizationFlowError(f"Authorization flow failed: {e}", e)
    
    async def _store_credentials(self, email: str, credentials: Credentials) -> None:
        """
        Store credentials in the token store.
        
        Args:
            email: Email address of the account
            credentials: Credentials to store
            
        Raises:
            TokenStorageError: If storing the token fails
        """
        try:
            # Extract token data from credentials
            token_data = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_type": "Bearer",
                "expires_in": None,
                "metadata": {},
            }
            
            # Calculate expires_in if expiry is available
            if credentials.expiry:
                now = datetime.now()
                expires_in = int((credentials.expiry - now).total_seconds())
                if expires_in > 0:
                    token_data["expires_in"] = expires_in
            
            # Add scopes if available
            if hasattr(credentials, "scopes") and credentials.scopes:
                token_data["scopes"] = credentials.scopes
            
            # Add client_id and client_secret to metadata
            if hasattr(credentials, "client_id") and credentials.client_id:
                token_data["metadata"]["client_id"] = credentials.client_id
            if hasattr(credentials, "client_secret") and credentials.client_secret:
                token_data["metadata"]["client_secret"] = credentials.client_secret
            
            # Store in token store (run in thread to avoid blocking)
            await asyncio.to_thread(
                self.token_store.store_token,
                email,
                token_data["access_token"],
                token_data["refresh_token"],
                token_data["token_type"],
                token_data["expires_in"],
                token_data.get("scopes"),
                token_data["metadata"],
            )
            
            logger.debug(f"Stored credentials for {email}")
        except Exception as e:
            logger.error(f"Error storing credentials for {email}: {e}", exc_info=True)
            raise TokenStorageError(f"Failed to store credentials: {e}", e)
    
    async def revoke_credentials(self, email: Optional[str] = None) -> bool:
        """
        Revoke credentials for an account.
        
        Args:
            email: Email address of the account (optional, uses default if not provided)
            
        Returns:
            True if credentials were revoked, False otherwise
            
        Raises:
            TokenRevocationError: If revocation fails
        """
        try:
            # Use default email if not provided
            if not email:
                email = await self._get_default_email()
            
            # Get credentials from token store
            try:
                token_data = await asyncio.to_thread(self.token_store.get_token, email)
                credentials = self._token_data_to_credentials(token_data)
            except TokenNotFoundError:
                logger.info(f"No token found for {email}, nothing to revoke")
                return False
            
            # Revoke the token
            if credentials.token:
                request = Request()
                await asyncio.to_thread(credentials.revoke, request)
            
            # Delete from token store
            deleted = await asyncio.to_thread(self.token_store.delete_token, email)
            
            # Cancel refresh task if running
            self._cancel_refresh_task(email)
            
            logger.info(f"Revoked credentials for {email}")
            return deleted
        
        except Exception as e:
            logger.error(f"Error revoking credentials for {email}: {e}", exc_info=True)
            raise TokenRevocationError(f"Failed to revoke credentials: {e}", e)
    
    async def force_reauthorize(self, email: Optional[str] = None) -> Credentials:
        """
        Force a new authorization flow, even if valid credentials exist.
        
        This method is used by the /reauthorize command.
        
        Args:
            email: Email address of the account (optional, uses default if not provided)
            
        Returns:
            New OAuth credentials
            
        Raises:
            AuthorizationFlowError: If the authorization flow fails
        """
        try:
            # Use default email if not provided
            if not email:
                email = await self._get_default_email()
            
            # Revoke existing credentials if any
            try:
                await self.revoke_credentials(email)
            except Exception as e:
                logger.warning(f"Error revoking credentials during reauthorization: {e}")
            
            # Run new auth flow
            credentials = await self._run_auth_flow(email)
            
            logger.info(f"Successfully reauthorized {email}")
            return credentials
        
        except Exception as e:
            logger.error(f"Reauthorization failed: {e}", exc_info=True)
            raise AuthorizationFlowError(f"Reauthorization failed: {e}", e)
    
    async def check_auth_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Check authentication status for all accounts.
        
        Returns:
            Dictionary mapping email to auth status details
        """
        try:
            # Get all accounts from token store
            accounts = await asyncio.to_thread(self.token_store.list_accounts)
            
            result = {}
            for account in accounts:
                email = account["email"]
                
                # Build status dict
                status = {
                    "valid": account["has_token"] and not account["is_expired"],
                    "has_refresh_token": account["has_refresh_token"],
                    "expires_at": account.get("expires_at"),
                    "last_updated": account.get("updated_at"),
                }
                
                result[email] = status
            
            return result
        
        except Exception as e:
            logger.error(f"Error checking auth status: {e}", exc_info=True)
            return {}
    
    def _token_data_to_credentials(self, token_data: Dict[str, Any]) -> Credentials:
        """
        Convert token data from storage to Credentials object.
        
        Args:
            token_data: Token data from storage
            
        Returns:
            Credentials object
        """
        # Extract metadata
        metadata = token_data.get("metadata", {})
        client_id = metadata.get("client_id")
        client_secret = metadata.get("client_secret")
        
        # If client_id/secret not in metadata, try to get from credentials file
        if not client_id or not client_secret:
            try:
                with open(self.credentials_path, "r") as f:
                    client_info = json.load(f)
                    if "installed" in client_info:
                        client_id = client_info["installed"].get("client_id")
                        client_secret = client_info["installed"].get("client_secret")
                    elif "web" in client_info:
                        client_id = client_info["web"].get("client_id")
                        client_secret = client_info["web"].get("client_secret")
            except Exception as e:
                logger.warning(f"Could not load client info from credentials file: {e}")
        
        # Parse expiry if available
        expiry = None
        if token_data.get("expires_at"):
            try:
                expiry = datetime.fromisoformat(token_data["expires_at"])
            except (ValueError, TypeError):
                pass
        
        # Create Credentials object
        return Credentials(
            token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=token_data.get("scopes", self.settings.scopes),
            expiry=expiry,
        )
    
    async def _get_default_email(self) -> str:
        """
        Get the default email address from client secrets or a stored token.
        
        Returns:
            Default email address, or "default@gmail.com" if not found
        """
        # Try to get from a stored token
        try:
            accounts = await asyncio.to_thread(self.token_store.list_accounts)
            if accounts:
                return accounts[0]["email"]
        except Exception as e:
            logger.debug(f"Could not get default email from token store: {e}")
        
        # Default fallback
        return "default@gmail.com"
    
    async def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """
        Get user info from Google using the provided credentials.
        
        Args:
            credentials: OAuth credentials
            
        Returns:
            User info dictionary
        """
        try:
            # Build the service in a thread
            service = await asyncio.to_thread(
                build, "oauth2", "v2", credentials=credentials
            )
            
            # Get user info in a thread
            user_info = await asyncio.to_thread(
                service.userinfo().get().execute
            )
            
            return user_info
        except Exception as e:
            logger.warning(f"Could not get user info: {e}")
            return {}
    
    def _ensure_refresh_task(self, email: str, credentials: Credentials) -> None:
        """
        Ensure a background refresh task is running for the account.
        
        Args:
            email: Email address of the account
            credentials: Current credentials
        """
        # Cancel existing task if running
        self._cancel_refresh_task(email)
        
        # Only start task if credentials have an expiry and refresh token
        if not credentials.expiry or not credentials.refresh_token:
            return
        
        # Calculate time until refresh (default to 30 minutes before expiry)
        now = datetime.now()
        refresh_before = timedelta(minutes=self.settings.auto_refresh_before_expiry_minutes)
        refresh_at = credentials.expiry - refresh_before
        
        # If refresh time is in the past, schedule for immediate refresh
        if refresh_at <= now:
            delay = 0
        else:
            delay = (refresh_at - now).total_seconds()
        
        # Schedule the refresh task
        loop = asyncio.get_event_loop()
        task = loop.create_task(self._background_refresh(email, delay))
        self._refresh_tasks[email] = task
        
        logger.debug(
            f"Scheduled token refresh for {email} in {delay:.1f} seconds "
            f"(at {refresh_at.isoformat()})"
        )
    
    def _cancel_refresh_task(self, email: str) -> None:
        """
        Cancel a background refresh task for an account.
        
        Args:
            email: Email address of the account
        """
        task = self._refresh_tasks.pop(email, None)
        if task and not task.done():
            task.cancel()
            logger.debug(f"Cancelled refresh task for {email}")
    
    async def _background_refresh(self, email: str, delay: float) -> None:
        """
        Background task to refresh credentials before they expire.
        
        Args:
            email: Email address of the account
            delay: Seconds to wait before refreshing
        """
        try:
            # Wait until it's time to refresh
            if delay > 0:
                await asyncio.sleep(delay)
            
            logger.debug(f"Background refresh task running for {email}")
            
            # Get current credentials
            token_data = await asyncio.to_thread(self.token_store.get_token, email)
            credentials = self._token_data_to_credentials(token_data)
            
            # Refresh the credentials
            await self._refresh_credentials(email, credentials, force=True)
            
            logger.info(f"Background refresh successful for {email}")
            
            # Schedule next refresh
            if credentials.expiry:
                self._ensure_refresh_task(email, credentials)
        
        except asyncio.CancelledError:
            logger.debug(f"Background refresh task cancelled for {email}")
        
        except Exception as e:
            logger.error(f"Background refresh failed for {email}: {e}", exc_info=True)
