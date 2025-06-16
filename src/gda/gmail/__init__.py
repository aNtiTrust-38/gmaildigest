"""
Gmail module for Gmail Digest Assistant v2.0.

This module provides classes for interacting with the Gmail API, including
fetching, parsing, and manipulating emails, with support for batching,
error handling, and all core functionality needed for the application.
"""
from gda.gmail.models import (
    BatchRequest,
    BatchRequestItem,
    EmailAddress,
    EmailAttachment,
    EmailBody,
    EmailBodyPart,
    EmailHeader,
    EmailLabel,
    EmailMessage,
    EmailThread,
    GmailSearchQuery,
    LabelType,
    LabelVisibility,
    MessageImportance,
)
from gda.gmail.service import (
    GmailService,
    GmailServiceError,
    GmailRateLimitError,
    GmailBatchError,
)

__all__ = [
    # Service classes
    "GmailService",
    "GmailServiceError",
    "GmailRateLimitError",
    "GmailBatchError",
    
    # Model classes
    "BatchRequest",
    "BatchRequestItem",
    "EmailAddress",
    "EmailAttachment",
    "EmailBody",
    "EmailBodyPart",
    "EmailHeader",
    "EmailLabel",
    "EmailMessage",
    "EmailThread",
    "GmailSearchQuery",
    "LabelType",
    "LabelVisibility",
    "MessageImportance",
]
