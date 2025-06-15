"""
Gmail OAuth2 Authentication Module
"""
import os
import pickle
import time
import logging
from datetime import datetime
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the token.pickle file.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # Read-only access to Gmail
    'https://www.googleapis.com/auth/gmail.modify',    # Modify emails (for marking as read)
    'https://www.googleapis.com/auth/gmail.labels',    # Manage labels
    'https://www.googleapis.com/auth/calendar.events', # Manage calendar events
]

class GmailAuthenticator:
    """Handles Gmail API authentication using OAuth 2.0"""
    
    def __init__(self):
        self.credentials_path = os.getenv('CREDENTIALS_PATH', 'credentials.json')
        self.token_path = Path('token.pickle')
        # Logger
        self.logger = logging.getLogger(__name__)
        if not self.logger.hasHandlers():
            logging.basicConfig(level=logging.INFO)
    
    # --------------------------------------------------------------------- #
    # Internal helpers                                                      #
    # --------------------------------------------------------------------- #

    def _save_credentials(self, credentials: Credentials) -> None:
        """
        Persist credentials to disk together with minimal metadata.
        The resulting pickle structure is backward-compatible: older
        versions that expect a Credentials object will still be able to
        unpickle the first element of the dict (`creds`).
        """
        try:
            payload = {
                "creds": credentials,
                "saved_at": datetime.utcnow()
            }
            with open(self.token_path, "wb") as token_file:
                pickle.dump(payload, token_file)
            # Tighten permissions so only the user can read/write
            try:
                os.chmod(self.token_path, 0o600)
            except Exception:
                # Ignore chmod issues on non-POSIX OSes
                pass
            self.logger.debug("OAuth token saved to %s", self.token_path)
        except Exception as exc:
            # Don't raise – failing to write must not crash the app
            self.logger.error("Failed to write token file: %s", exc, exc_info=True)

    def _load_credentials(self):
        """
        Load credentials from token file.
        Supports both legacy (Credentials) and new (dict) formats.
        """
        if not self.token_path.exists():
            return None
        try:
            with open(self.token_path, "rb") as token_file:
                data = pickle.load(token_file)
            # Determine structure
            if isinstance(data, Credentials):
                return data
            if isinstance(data, dict):
                return data.get("creds") or data.get("credentials")
        except Exception as exc:
            self.logger.warning("Error loading token: %s", exc, exc_info=True)
        return None

    # --------------------------------------------------------------------- #
    # Public methods                                                        #
    # --------------------------------------------------------------------- #

    def get_credentials(self):
        """
        Gets valid user credentials from storage or initiates OAuth2 flow.
        
        Returns:
            Credentials: The obtained credentials.
        """
        credentials = self._load_credentials()

        # Check if credentials are valid
        if credentials and credentials.valid:
            return credentials
            
        # Refresh token if expired
        if credentials and credentials.expired and credentials.refresh_token:
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    credentials.refresh(Request())
                    self.logger.info("OAuth token refreshed successfully")
                    # Persist updated tokens to disk to extend expiry
                    self._save_credentials(credentials)
                    return credentials
                except Exception as exc:
                    wait_time = 2 ** attempt
                    self.logger.warning(
                        "Error refreshing token (attempt %d/%d): %s",
                        attempt + 1,
                        max_attempts,
                        exc,
                        exc_info=True,
                    )
                    time.sleep(wait_time)
            # If all attempts failed, force reauthorization
            self.logger.error("Failed to refresh OAuth token after retries")
            credentials = None

        # If no valid credentials available, initiate OAuth flow
        if not credentials:
            credentials = self.force_reauthorize()

        return credentials

    # ------------------------------------------------------------------ #
    # Extra utilities                                                    #
    # ------------------------------------------------------------------ #

    def force_reauthorize(self) -> Credentials:
        """
        Delete any stored token and run a fresh OAuth flow.
        Returns fresh credentials or raises Exception on failure.
        Intended to be called by the Telegram bot (/reauthorize command).
        """
        # Remove old token file
        if self.token_path.exists():
            try:
                self.token_path.unlink()
            except Exception as exc:
                self.logger.warning("Could not delete old token file: %s", exc)
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES
            )
            self.logger.info("Opening browser for new OAuth authorization…")
            credentials = flow.run_local_server(port=0)
            self._save_credentials(credentials)
            self.logger.info("Successfully obtained and stored new credentials")
            return credentials
        except Exception as exc:
            self.logger.error("Failed to authenticate: %s", exc, exc_info=True)
            raise

    def revoke_credentials(self):
        """
        Revokes the current credentials and deletes the token file.
        """
        if self.token_path.exists():
            try:
                credentials = self.get_credentials()
                if credentials:
                    credentials.revoke(Request())
                self.token_path.unlink()
                print("Successfully revoked credentials and deleted token.")
            except Exception as e:
                print(f"Error revoking credentials: {e}")
                
    def verify_credentials(self):
        """
        Verifies that credentials can be obtained and are valid.
        
        Returns:
            bool: True if credentials are valid, False otherwise.
        """
        try:
            credentials = self.get_credentials()
            return credentials and credentials.valid
        except Exception as e:
            print(f"Error verifying credentials: {e}")
            return False 