"""
Token storage module for Gmail Digest Assistant v2.

This module provides secure storage for OAuth tokens using SQLite with optional
encryption via SQLCipher. It supports storing tokens for multiple accounts,
with metadata like creation time, expiry, etc.
"""
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

from gda.auth.exceptions import (
    TokenNotFoundError,
    TokenStorageError,
    EncryptionError,
)

# Configure logger
logger = logging.getLogger(__name__)


class TokenStore:
    """
    Secure storage for OAuth tokens using SQLite with optional encryption.
    
    This class provides methods to store, retrieve, update, and delete OAuth tokens
    for multiple accounts. When an encryption key is provided, it uses SQLCipher
    to encrypt the database.
    """
    
    def __init__(
        self,
        db_path: Union[str, Path],
        encryption_key: Optional[str] = None,
        auto_create: bool = True,
    ):
        """
        Initialize the token store.
        
        Args:
            db_path: Path to the SQLite database file
            encryption_key: Optional encryption key for the database
            auto_create: Whether to automatically create the database if it doesn't exist
        
        Raises:
            TokenStorageError: If there's an error initializing the store
            EncryptionError: If encryption is requested but not available
        """
        self.db_path = Path(db_path)
        self.encryption_key = encryption_key
        self.use_encryption = encryption_key is not None
        
        # Validate encryption availability
        if self.use_encryption and not ENCRYPTION_AVAILABLE:
            raise EncryptionError(
                "Encryption requested but pysqlcipher3 is not installed. "
                "Install with: pip install pysqlcipher3"
            )
        
        # Create database if it doesn't exist and auto_create is True
        if auto_create and (not self.db_path.exists() or self.db_path.stat().st_size == 0):
            self._create_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a connection to the database.
        
        Returns:
            A connection to the SQLite database
            
        Raises:
            TokenStorageError: If there's an error connecting to the database
            EncryptionError: If there's an error with the encryption key
        """
        try:
            if self.use_encryption:
                # Use SQLCipher for encrypted database
                conn = sqlcipher.connect(str(self.db_path))
                conn.execute(f"PRAGMA key = '{self.encryption_key}'")
                # Verify the key works by executing a simple query
                try:
                    conn.execute("SELECT count(*) FROM sqlite_master")
                except sqlcipher.DatabaseError:
                    raise EncryptionError("Invalid encryption key or corrupted database")
            else:
                # Use standard SQLite for unencrypted database
                conn = sqlite3.connect(str(self.db_path))
            
            # Enable foreign keys and configure connection
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            
            return conn
        except (sqlite3.Error, sqlcipher.Error) as e:
            if self.use_encryption and "not an encrypted database" in str(e).lower():
                raise EncryptionError(
                    "Database is not encrypted but encryption key was provided"
                )
            elif self.use_encryption and "file is not a database" in str(e).lower():
                raise EncryptionError("Invalid encryption key or corrupted database")
            else:
                raise TokenStorageError(f"Error connecting to token database: {e}", e)
    
    def _create_database(self) -> None:
        """
        Create the token database schema.
        
        Raises:
            TokenStorageError: If there's an error creating the database
        """
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect and create schema
            with self._get_connection() as conn:
                conn.executescript("""
                -- Accounts table
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Tokens table
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_type TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    scopes TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );
                
                -- Token metadata table
                CREATE TABLE IF NOT EXISTS token_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    FOREIGN KEY (token_id) REFERENCES tokens(id) ON DELETE CASCADE,
                    UNIQUE (token_id, key)
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_tokens_account_id ON tokens(account_id);
                CREATE INDEX IF NOT EXISTS idx_token_metadata_token_id ON token_metadata(token_id);
                """)
            
            logger.info(f"Created token database at {self.db_path}")
        except Exception as e:
            raise TokenStorageError(f"Error creating token database: {e}", e)
    
    def store_token(
        self,
        email: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_type: str = "Bearer",
        expires_in: Optional[int] = None,
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store a token for an account.
        
        Args:
            email: Email address of the account
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            token_type: Token type (default: Bearer)
            expires_in: Token expiry in seconds from now (optional)
            scopes: List of OAuth scopes (optional)
            metadata: Additional metadata to store with the token (optional)
            
        Raises:
            TokenStorageError: If there's an error storing the token
        """
        try:
            with self._get_connection() as conn:
                # Calculate expiry time if provided
                expires_at = None
                if expires_in:
                    expires_at = datetime.now() + timedelta(seconds=expires_in)
                    expires_at_str = expires_at.isoformat()
                else:
                    expires_at_str = None
                
                # Convert scopes to string if provided
                scopes_str = None
                if scopes:
                    scopes_str = json.dumps(scopes)
                
                # Get or create account
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO accounts (email) VALUES (?)",
                    (email,)
                )
                cursor.execute(
                    "SELECT id FROM accounts WHERE email = ?",
                    (email,)
                )
                account_id = cursor.fetchone()[0]
                
                # Delete existing token for this account if it exists
                cursor.execute(
                    "DELETE FROM tokens WHERE account_id = ?",
                    (account_id,)
                )
                
                # Insert new token
                cursor.execute(
                    """
                    INSERT INTO tokens 
                    (account_id, access_token, refresh_token, token_type, expires_at, scopes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (account_id, access_token, refresh_token, token_type, expires_at_str, scopes_str)
                )
                token_id = cursor.lastrowid
                
                # Store metadata if provided
                if metadata and token_id:
                    for key, value in metadata.items():
                        # Convert non-string values to JSON
                        if not isinstance(value, str):
                            value = json.dumps(value)
                        
                        cursor.execute(
                            """
                            INSERT INTO token_metadata (token_id, key, value)
                            VALUES (?, ?, ?)
                            """,
                            (token_id, key, value)
                        )
                
                conn.commit()
                logger.debug(f"Stored token for account: {email}")
        except Exception as e:
            raise TokenStorageError(f"Error storing token: {e}", e)
    
    def get_token(self, email: str) -> Dict[str, Any]:
        """
        Get a token for an account.
        
        Args:
            email: Email address of the account
            
        Returns:
            Token data as a dictionary
            
        Raises:
            TokenNotFoundError: If no token is found for the account
            TokenStorageError: If there's an error retrieving the token
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT t.*, a.email
                    FROM tokens t
                    JOIN accounts a ON t.account_id = a.id
                    WHERE a.email = ?
                    """,
                    (email,)
                )
                token_row = cursor.fetchone()
                
                if not token_row:
                    raise TokenNotFoundError(email)
                
                # Convert row to dict
                token_data = dict(token_row)
                
                # Parse scopes if present
                if token_data.get("scopes"):
                    token_data["scopes"] = json.loads(token_data["scopes"])
                
                # Get metadata
                cursor.execute(
                    """
                    SELECT key, value
                    FROM token_metadata
                    WHERE token_id = ?
                    """,
                    (token_data["id"],)
                )
                metadata = {}
                for row in cursor.fetchall():
                    key, value = row
                    # Try to parse JSON values
                    try:
                        metadata[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        metadata[key] = value
                
                token_data["metadata"] = metadata
                
                return token_data
        except TokenNotFoundError:
            raise
        except Exception as e:
            raise TokenStorageError(f"Error retrieving token: {e}", e)
    
    def update_token(
        self,
        email: str,
        access_token: str,
        expires_in: Optional[int] = None,
        refresh_token: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update a token for an account.
        
        Args:
            email: Email address of the account
            access_token: New access token
            expires_in: New expiry time in seconds from now (optional)
            refresh_token: New refresh token (optional, only updated if provided)
            metadata_updates: Metadata to update (optional)
            
        Raises:
            TokenNotFoundError: If no token is found for the account
            TokenStorageError: If there's an error updating the token
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get account and token IDs
                cursor.execute(
                    """
                    SELECT a.id as account_id, t.id as token_id
                    FROM accounts a
                    LEFT JOIN tokens t ON a.id = t.account_id
                    WHERE a.email = ?
                    """,
                    (email,)
                )
                row = cursor.fetchone()
                
                if not row or row["token_id"] is None:
                    raise TokenNotFoundError(email)
                
                account_id = row["account_id"]
                token_id = row["token_id"]
                
                # Calculate expiry time if provided
                expires_at = None
                if expires_in:
                    expires_at = datetime.now() + timedelta(seconds=expires_in)
                    expires_at_str = expires_at.isoformat()
                else:
                    expires_at_str = None
                
                # Update token
                update_fields = ["access_token = ?", "updated_at = CURRENT_TIMESTAMP"]
                update_values = [access_token]
                
                if expires_at_str:
                    update_fields.append("expires_at = ?")
                    update_values.append(expires_at_str)
                
                if refresh_token:
                    update_fields.append("refresh_token = ?")
                    update_values.append(refresh_token)
                
                update_query = f"""
                UPDATE tokens
                SET {', '.join(update_fields)}
                WHERE id = ?
                """
                update_values.append(token_id)
                
                cursor.execute(update_query, update_values)
                
                # Update metadata if provided
                if metadata_updates:
                    for key, value in metadata_updates.items():
                        # Convert non-string values to JSON
                        if not isinstance(value, str):
                            value = json.dumps(value)
                        
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO token_metadata (token_id, key, value)
                            VALUES (?, ?, ?)
                            """,
                            (token_id, key, value)
                        )
                
                conn.commit()
                logger.debug(f"Updated token for account: {email}")
        except TokenNotFoundError:
            raise
        except Exception as e:
            raise TokenStorageError(f"Error updating token: {e}", e)
    
    def delete_token(self, email: str) -> bool:
        """
        Delete a token for an account.
        
        Args:
            email: Email address of the account
            
        Returns:
            True if a token was deleted, False if no token existed
            
        Raises:
            TokenStorageError: If there's an error deleting the token
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get account ID
                cursor.execute(
                    "SELECT id FROM accounts WHERE email = ?",
                    (email,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return False
                
                account_id = row[0]
                
                # Delete token (cascade will delete metadata)
                cursor.execute(
                    "DELETE FROM tokens WHERE account_id = ?",
                    (account_id,)
                )
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                if deleted:
                    logger.debug(f"Deleted token for account: {email}")
                
                return deleted
        except Exception as e:
            raise TokenStorageError(f"Error deleting token: {e}", e)
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """
        List all accounts with tokens.
        
        Returns:
            List of account dictionaries with email and token status
            
        Raises:
            TokenStorageError: If there's an error listing accounts
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        a.email,
                        t.id IS NOT NULL as has_token,
                        t.expires_at,
                        t.refresh_token IS NOT NULL as has_refresh_token,
                        t.created_at,
                        t.updated_at
                    FROM accounts a
                    LEFT JOIN tokens t ON a.id = t.account_id
                    """
                )
                
                accounts = []
                for row in cursor.fetchall():
                    account = dict(row)
                    
                    # Parse expires_at if present
                    if account.get("expires_at"):
                        try:
                            account["expires_at"] = datetime.fromisoformat(account["expires_at"])
                            account["is_expired"] = datetime.now() > account["expires_at"]
                        except (ValueError, TypeError):
                            account["is_expired"] = None
                    else:
                        account["is_expired"] = None
                    
                    accounts.append(account)
                
                return accounts
        except Exception as e:
            raise TokenStorageError(f"Error listing accounts: {e}", e)
    
    def check_token_expiry(self, email: str) -> Tuple[bool, Optional[datetime]]:
        """
        Check if a token is expired or about to expire.
        
        Args:
            email: Email address of the account
            
        Returns:
            Tuple of (is_expired, expires_at)
            
        Raises:
            TokenNotFoundError: If no token is found for the account
            TokenStorageError: If there's an error checking expiry
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT t.expires_at
                    FROM tokens t
                    JOIN accounts a ON t.account_id = a.id
                    WHERE a.email = ?
                    """,
                    (email,)
                )
                row = cursor.fetchone()
                
                if not row:
                    raise TokenNotFoundError(email)
                
                expires_at_str = row["expires_at"]
                if not expires_at_str:
                    # No expiry time set
                    return False, None
                
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    is_expired = datetime.now() > expires_at
                    return is_expired, expires_at
                except (ValueError, TypeError):
                    # Invalid expiry time
                    return False, None
        except TokenNotFoundError:
            raise
        except Exception as e:
            raise TokenStorageError(f"Error checking token expiry: {e}", e)
    
    def get_token_metadata(self, email: str, key: str) -> Any:
        """
        Get a specific metadata value for a token.
        
        Args:
            email: Email address of the account
            key: Metadata key
            
        Returns:
            Metadata value, or None if not found
            
        Raises:
            TokenNotFoundError: If no token is found for the account
            TokenStorageError: If there's an error retrieving metadata
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT m.value
                    FROM token_metadata m
                    JOIN tokens t ON m.token_id = t.id
                    JOIN accounts a ON t.account_id = a.id
                    WHERE a.email = ? AND m.key = ?
                    """,
                    (email, key)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                value = row["value"]
                
                # Try to parse JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
        except Exception as e:
            if "no such table" in str(e).lower():
                # Database might not be fully initialized
                raise TokenNotFoundError(email)
            raise TokenStorageError(f"Error retrieving token metadata: {e}", e)
    
    def set_token_metadata(self, email: str, key: str, value: Any) -> None:
        """
        Set a metadata value for a token.
        
        Args:
            email: Email address of the account
            key: Metadata key
            value: Metadata value
            
        Raises:
            TokenNotFoundError: If no token is found for the account
            TokenStorageError: If there's an error setting metadata
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get token ID
                cursor.execute(
                    """
                    SELECT t.id
                    FROM tokens t
                    JOIN accounts a ON t.account_id = a.id
                    WHERE a.email = ?
                    """,
                    (email,)
                )
                row = cursor.fetchone()
                
                if not row:
                    raise TokenNotFoundError(email)
                
                token_id = row["id"]
                
                # Convert non-string values to JSON
                if not isinstance(value, str):
                    value = json.dumps(value)
                
                # Insert or replace metadata
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO token_metadata (token_id, key, value)
                    VALUES (?, ?, ?)
                    """,
                    (token_id, key, value)
                )
                
                conn.commit()
        except TokenNotFoundError:
            raise
        except Exception as e:
            raise TokenStorageError(f"Error setting token metadata: {e}", e)
    
    def vacuum(self) -> None:
        """
        Optimize the database by running VACUUM.
        
        Raises:
            TokenStorageError: If there's an error optimizing the database
        """
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
                logger.debug("Optimized token database with VACUUM")
        except Exception as e:
            raise TokenStorageError(f"Error optimizing database: {e}", e)
    
    def change_encryption_key(self, new_key: Optional[str]) -> None:
        """
        Change the encryption key for the database.
        
        Args:
            new_key: New encryption key, or None to decrypt the database
            
        Raises:
            TokenStorageError: If there's an error changing the encryption key
            EncryptionError: If encryption is not available
        """
        if not ENCRYPTION_AVAILABLE:
            raise EncryptionError(
                "Encryption operations require pysqlcipher3. "
                "Install with: pip install pysqlcipher3"
            )
        
        try:
            # Create a temporary database
            temp_path = self.db_path.with_suffix('.temp.db')
            if temp_path.exists():
                temp_path.unlink()
            
            # Export all data
            accounts = self.list_accounts()
            tokens = {}
            for account in accounts:
                email = account["email"]
                if account["has_token"]:
                    try:
                        tokens[email] = self.get_token(email)
                    except TokenNotFoundError:
                        pass
            
            # Create new database with new encryption key
            old_key = self.encryption_key
            self.encryption_key = new_key
            self.use_encryption = new_key is not None
            self.db_path = temp_path
            self._create_database()
            
            # Import all data to new database
            for email, token in tokens.items():
                self.store_token(
                    email=email,
                    access_token=token["access_token"],
                    refresh_token=token["refresh_token"],
                    token_type=token["token_type"],
                    scopes=token["scopes"],
                    metadata=token["metadata"],
                )
            
            # Swap databases
            original_path = self.db_path.with_suffix('.db')
            self.db_path = original_path
            
            # Close any open connections
            self.encryption_key = old_key
            self.use_encryption = old_key is not None
            
            # Rename files
            backup_path = original_path.with_suffix('.bak.db')
            if original_path.exists():
                original_path.rename(backup_path)
            temp_path.rename(original_path)
            
            # Update instance variables
            self.encryption_key = new_key
            self.use_encryption = new_key is not None
            
            # Clean up backup if everything succeeded
            if backup_path.exists():
                backup_path.unlink()
            
            logger.info("Changed database encryption key")
        except Exception as e:
            raise TokenStorageError(f"Error changing encryption key: {e}", e)
