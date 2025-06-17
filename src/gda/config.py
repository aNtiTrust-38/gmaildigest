"""
Configuration module for Gmail Digest Assistant v2.

This module uses Pydantic Settings to handle loading environment variables,
secrets, and application configuration with proper typing and validation.
"""
import os
import json
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Set

from pydantic import (
    Field,
    validator,
    SecretStr,
    AnyHttpUrl,
    EmailStr,
    DirectoryPath,
    FilePath,
)
# NOTE: In Pydantic v2 `BaseSettings` lives in the dedicated
# `pydantic_settings` package.  Import it only from there to avoid
# duplication/attribute-error issues.
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Log levels for the application."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class AuthSettings(BaseSettings):
    """Authentication settings for Google OAuth."""
    credentials_path: Path = Field(
        default=Path("credentials.json"),
        description="Path to the Google OAuth credentials JSON file",
    )
    token_db_path: Path = Field(
        default=Path("token.db"),
        description="Path to the SQLite database for storing tokens",
    )
    token_encryption_key: Optional[SecretStr] = Field(
        default=None,
        description="Encryption key for token database (if None, no encryption)",
    )
    scopes: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.labels",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        description="OAuth scopes required by the application",
    )
    auto_refresh_before_expiry_minutes: int = Field(
        default=30,
        description="Minutes before token expiry to attempt refresh",
        ge=5,
        le=120,
    )
    max_refresh_retries: int = Field(
        default=3,
        description="Maximum number of token refresh retries",
        ge=1,
        le=10,
    )

    @validator("credentials_path", "token_db_path")
    def ensure_path_exists_or_creatable(cls, v: Path) -> Path:
        """Ensure the directory for the path exists or can be created."""
        if not v.parent.exists():
            try:
                v.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Cannot create directory for {v}: {e}")
        return v


class GmailSettings(BaseSettings):
    """Settings for Gmail service."""
    max_emails_per_query: int = Field(
        default=50,
        description="Maximum number of emails to fetch in a single query",
        ge=10,
        le=500,
    )
    default_query: str = Field(
        default="is:unread in:inbox",
        description="Default Gmail search query",
    )
    batch_size: int = Field(
        default=10,
        description="Batch size for Gmail API requests",
        ge=1,
        le=100,
    )
    forward_email: Optional[EmailStr] = Field(
        default=None,
        description="Email address to forward important emails to",
    )


class SummarySettings(BaseSettings):
    """Settings for email summarization."""
    anthropic_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Anthropic API key for Claude summarization",
    )
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key for GPT summarization",
    )
    max_summary_length: int = Field(
        default=400,
        description="Maximum length of email summaries in characters",
        ge=100,
        le=1000,
    )
    combined_summary_length: int = Field(
        default=800,
        description="Maximum length for combined summaries from same sender",
        ge=200,
        le=2000,
    )
    reading_speed_wpm: int = Field(
        default=225,
        description="Average reading speed in words per minute for time estimation",
        ge=100,
        le=500,
    )
    urgency_model_path: Optional[Path] = Field(
        default=None,
        description="Path to trained urgency classification model",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20240620",
        description="Anthropic model to use for summarization",
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use for summarization",
    )
    api_timeout_seconds: int = Field(
        default=15,
        description="Timeout for API calls in seconds",
        ge=5,
        le=60,
    )


class CalendarSettings(BaseSettings):
    """Settings for calendar integration."""
    default_reminder_minutes: int = Field(
        default=60,
        description="Default reminder time in minutes before event",
        ge=0,
        le=1440,
    )
    conflict_tag: str = Field(
        default="**CONFLICT**",
        description="Tag to add to event title when conflicts detected",
    )
    max_conflict_lookahead_days: int = Field(
        default=30,
        description="Maximum days to look ahead for calendar conflicts",
        ge=1,
        le=90,
    )
    enable_event_detection: bool = Field(
        default=True,
        description="Enable automatic event detection in emails",
    )


class TelegramSettings(BaseSettings):
    """Settings for Telegram bot."""
    bot_token: SecretStr = Field(
        ...,  # Required field
        description="Telegram bot token from BotFather",
    )
    allowed_chat_ids: Optional[Set[int]] = Field(
        default=None,
        description="Set of allowed chat IDs (if None, all chats are allowed)",
    )
    default_digest_interval_hours: float = Field(
        default=2.0,
        description="Default interval for digest updates in hours",
        ge=0.5,
        le=24.0,
    )
    check_interval_minutes: int = Field(
        default=15,
        description="Interval to check for important emails in minutes",
        ge=5,
        le=60,
    )
    max_message_length: int = Field(
        default=4000,
        description="Maximum length of Telegram messages (slightly under 4096 limit)",
        ge=1000,
        le=4000,
    )


class AppSettings(BaseSettings):
    """Main application settings."""
    app_name: str = Field(
        default="Gmail Digest Assistant",
        description="Name of the application",
    )
    version: str = Field(
        default="2.0.0",
        description="Application version",
    )
    environment: Environment = Field(
        default=Environment.PRODUCTION,
        description="Application environment",
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level",
    )
    data_dir: DirectoryPath = Field(
        default=Path("./data"),
        description="Directory for application data",
    )
    enable_analytics: bool = Field(
        default=False,
        description="Enable anonymous usage analytics",
    )
    plugins_dir: Optional[DirectoryPath] = Field(
        default=None,
        description="Directory for plugins (if None, plugins are disabled)",
    )

    @validator("data_dir")
    def ensure_data_dir_exists(cls, v: Path) -> Path:
        """Ensure the data directory exists or create it."""
        if not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        return v


class Settings(BaseSettings):
    """Root settings class combining all application settings."""
    model_config = SettingsConfigDict(
        env_file=".env.json",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    app: AppSettings = Field(default_factory=AppSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    gmail: GmailSettings = Field(default_factory=GmailSettings)
    summary: SummarySettings = Field(default_factory=SummarySettings)
    calendar: CalendarSettings = Field(default_factory=CalendarSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)

    @classmethod
    def from_json(cls, file_path: Union[str, Path]) -> "Settings":
        """Load settings from a JSON file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with open(file_path, "r") as f:
            config_data = json.load(f)
        
        return cls.parse_obj(config_data)
    
    def save_to_json(self, file_path: Union[str, Path]) -> None:
        """Save settings to a JSON file."""
        file_path = Path(file_path)
        
        # Ensure directory exists
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict, handling SecretStr
        config_dict = self.dict(exclude_none=True)
        
        # Save to file
        with open(file_path, "w") as f:
            json.dump(config_dict, f, indent=2)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance, initializing if necessary."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def load_settings(file_path: Optional[Union[str, Path]] = None) -> Settings:
    """Load settings from a file or environment variables."""
    global _settings
    
    if file_path:
        _settings = Settings.from_json(file_path)
    else:
        _settings = Settings()
    
    return _settings
