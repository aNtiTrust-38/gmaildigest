"""
Gmail Digest Assistant (GDA) v2.0

An intelligent email companion that helps manage Gmail inbox by creating
summarized digests of emails with smart grouping and actionable integrations
through Telegram.

This package provides a modular, async-first implementation with persistent
OAuth, tiered summarization, and calendar integration.
"""

__version__ = "2.0.0"
__author__ = "Kai Peace"
__email__ = "kai@peacefamily.us"
__license__ = "MIT"

# Import key components for easier access
from gda.config import get_settings, load_settings, Settings
from gda.auth import AuthManager, TokenStore, AuthError

# Version information tuple (major, minor, patch)
VERSION = tuple(map(int, __version__.split(".")))

# Expose main entry point
def run():
    """Run the Gmail Digest Assistant application."""
    from gda.cli import main
    main()
