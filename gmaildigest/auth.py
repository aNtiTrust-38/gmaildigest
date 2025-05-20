"""
Gmail OAuth2 Authentication Module
"""
import os
import pickle
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
    
    def get_credentials(self):
        """
        Gets valid user credentials from storage or initiates OAuth2 flow.
        
        Returns:
            Credentials: The obtained credentials.
        """
        credentials = None

        # Try to load existing token
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token:
                    credentials = pickle.load(token)
            except Exception as e:
                print(f"Error loading token: {e}")

        # Check if credentials are valid
        if credentials and credentials.valid:
            return credentials
            
        # Refresh token if expired
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                credentials = None

        # If no valid credentials available, initiate OAuth flow
        if not credentials:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                credentials = flow.run_local_server(port=0)
                
                # Save the credentials for future use
                with open(self.token_path, 'wb') as token:
                    pickle.dump(credentials, token)
                    
                print("Successfully obtained and saved new credentials.")
            except Exception as e:
                raise Exception(f"Failed to authenticate: {e}")

        return credentials

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