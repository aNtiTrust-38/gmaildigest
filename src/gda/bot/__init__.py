"""
Telegram bot module for Gmail Digest Assistant v2.

This module provides the BotApp class for Telegram bot integration,
command handling, and interactive UI.
"""
from typing import Dict, List, Optional, Any, Union

# Import the actual BotApp implementation
from gda.bot.app import BotApp
from gda.bot.commands import CommandRegistry
from gda.bot.handlers import (
    DigestHandler,
    SettingsHandler,
    AuthHandler,
    CalendarHandler,
)
from gda.bot.ui import ButtonFactory, MessageFormatter

__all__ = [
    "BotApp",
    "CommandRegistry",
    "DigestHandler",
    "SettingsHandler",
    "AuthHandler",
    "CalendarHandler",
    "ButtonFactory",
    "MessageFormatter",
]
