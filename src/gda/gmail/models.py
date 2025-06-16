"""
Pydantic models for Gmail API entities.

This module defines data models for Gmail messages, threads, labels, and other
entities using Pydantic for validation and serialization.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Union, Any

from pydantic import BaseModel, EmailStr, Field, HttpUrl, validator


class LabelType(str, Enum):
    """Gmail label types."""
    SYSTEM = "system"
    USER = "user"


class LabelVisibility(str, Enum):
    """Gmail label visibility settings."""
    LABEL_SHOW = "labelShow"
    LABEL_HIDE = "labelHide"
    LABEL_SHOW_IF_UNREAD = "labelShowIfUnread"


class MessageImportance(str, Enum):
    """Email importance levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    IMPORTANT_SENDER = "important_sender"


class EmailAddress(BaseModel):
    """Model for email address with optional name."""
    name: Optional[str] = None
    email: EmailStr
    
    def __str__(self) -> str:
        """String representation of email address."""
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


class EmailLabel(BaseModel):
    """Model for Gmail label."""
    id: str
    name: str
    type: LabelType = LabelType.USER
    visibility: Optional[LabelVisibility] = None
    message_list_visibility: Optional[LabelVisibility] = None
    label_list_visibility: Optional[LabelVisibility] = None
    color: Optional[Dict[str, str]] = None
    
    class Config:
        """Pydantic config."""
        use_enum_values = True


class EmailAttachment(BaseModel):
    """Model for email attachment."""
    attachment_id: str
    filename: str
    mime_type: str
    size: int
    content_id: Optional[str] = None
    data: Optional[bytes] = None
    inline: bool = False
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


class EmailBodyPart(BaseModel):
    """Model for a part of an email body (MIME part)."""
    mime_type: str
    content: str
    truncated: bool = False
    size: Optional[int] = None
    attachment: Optional[EmailAttachment] = None
    parts: Optional[List['EmailBodyPart']] = None


class EmailBody(BaseModel):
    """Model for email body content."""
    plain_text: Optional[str] = None
    html: Optional[str] = None
    truncated: bool = False
    size: Optional[int] = None
    parts: Optional[List[EmailBodyPart]] = None
    
    @validator('plain_text', 'html')
    def check_content_not_empty(cls, v, values):
        """Ensure at least one of plain_text or html is provided."""
        if v is None and not values.get('parts') and not (
            'plain_text' in values and values['plain_text'] is not None or
            'html' in values and values['html'] is not None
        ):
            raise ValueError("At least one of plain_text, html, or parts must be provided")
        return v


class EmailHeader(BaseModel):
    """Model for email header."""
    name: str
    value: str


class EmailMessage(BaseModel):
    """Model for Gmail message."""
    id: str
    thread_id: str
    history_id: Optional[str] = None
    
    # Core email fields
    subject: Optional[str] = ""
    from_: Optional[Union[EmailAddress, List[EmailAddress]]] = Field(default=None, alias="from")
    to: Optional[List[EmailAddress]] = None
    cc: Optional[List[EmailAddress]] = None
    bcc: Optional[List[EmailAddress]] = None
    reply_to: Optional[List[EmailAddress]] = None
    
    # Content
    body: Optional[EmailBody] = None
    snippet: Optional[str] = None
    attachments: List[EmailAttachment] = Field(default_factory=list)
    
    # Metadata
    date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    labels: List[str] = Field(default_factory=list)
    label_objects: List[EmailLabel] = Field(default_factory=list)
    headers: List[EmailHeader] = Field(default_factory=list)
    
    # Status flags
    is_unread: bool = True
    is_starred: bool = False
    is_draft: bool = False
    is_sent: bool = False
    is_inbox: bool = True
    is_trash: bool = False
    is_spam: bool = False
    
    # Importance and urgency
    importance: MessageImportance = MessageImportance.NORMAL
    urgency_score: float = 0.0  # 0.0 to 1.0
    urgency_reason: Optional[str] = None
    
    # Calendar-related
    has_calendar_event: bool = False
    calendar_event_details: Optional[Dict[str, Any]] = None
    
    # Internal tracking
    summary: Optional[str] = None
    summary_method: Optional[str] = None  # "anthropic", "openai", "sumy", "fallback"
    reading_time_minutes: Optional[float] = None
    
    class Config:
        """Pydantic config."""
        allow_population_by_field_name = True
        use_enum_values = True
    
    @validator('from_', 'to', 'cc', 'bcc', 'reply_to', pre=True)
    def parse_email_addresses(cls, v):
        """Parse email addresses from strings or dicts."""
        if v is None:
            return v
            
        if isinstance(v, str):
            # Simple email string
            return EmailAddress(email=v)
            
        if isinstance(v, dict):
            # Single address as dict
            return EmailAddress(**v)
            
        if isinstance(v, list):
            # List of addresses
            result = []
            for addr in v:
                if isinstance(addr, str):
                    result.append(EmailAddress(email=addr))
                elif isinstance(addr, dict):
                    result.append(EmailAddress(**addr))
                elif isinstance(addr, EmailAddress):
                    result.append(addr)
                else:
                    raise ValueError(f"Invalid email address format: {addr}")
            return result
            
        if isinstance(v, EmailAddress):
            return v
            
        raise ValueError(f"Invalid email address format: {v}")
    
    def get_header(self, name: str) -> Optional[str]:
        """Get a header value by name (case-insensitive)."""
        name_lower = name.lower()
        for header in self.headers:
            if header.name.lower() == name_lower:
                return header.value
        return None
    
    @property
    def is_important(self) -> bool:
        """Check if the message is marked as important."""
        return (self.importance in 
                [MessageImportance.HIGH, MessageImportance.URGENT, 
                 MessageImportance.IMPORTANT_SENDER])
    
    @property
    def sender_address(self) -> Optional[str]:
        """Get the sender's email address as string."""
        if not self.from_:
            return None
        if isinstance(self.from_, list) and self.from_:
            return self.from_[0].email
        return self.from_.email
    
    @property
    def sender_name(self) -> Optional[str]:
        """Get the sender's name as string."""
        if not self.from_:
            return None
        if isinstance(self.from_, list) and self.from_:
            return self.from_[0].name
        return self.from_.name
    
    @property
    def plain_body(self) -> str:
        """Get the plain text body or empty string."""
        if not self.body:
            return ""
        return self.body.plain_text or ""
    
    @property
    def html_body(self) -> str:
        """Get the HTML body or empty string."""
        if not self.body:
            return ""
        return self.body.html or ""


class EmailThread(BaseModel):
    """Model for Gmail thread."""
    id: str
    history_id: Optional[str] = None
    messages: List[EmailMessage] = Field(default_factory=list)
    snippet: Optional[str] = None
    
    # Metadata
    labels: List[str] = Field(default_factory=list)
    
    # Status flags
    is_unread: bool = True
    
    # Importance and urgency (derived from messages)
    importance: MessageImportance = MessageImportance.NORMAL
    urgency_score: float = 0.0
    
    # Summary data
    combined_summary: Optional[str] = None
    summary_method: Optional[str] = None
    reading_time_minutes: Optional[float] = None
    
    @validator('importance', 'urgency_score', pre=True, always=True)
    def calculate_importance(cls, v, values):
        """Calculate importance and urgency from messages."""
        if not values.get('messages'):
            return v
            
        # For importance, take the highest importance level from messages
        if v == MessageImportance.NORMAL and 'importance' in values:
            importance_values = [msg.importance for msg in values['messages']]
            importance_order = [
                MessageImportance.NORMAL,
                MessageImportance.LOW,
                MessageImportance.HIGH,
                MessageImportance.URGENT,
                MessageImportance.IMPORTANT_SENDER
            ]
            
            highest_importance = MessageImportance.NORMAL
            for imp in importance_values:
                if importance_order.index(imp) > importance_order.index(highest_importance):
                    highest_importance = imp
            
            return highest_importance
            
        # For urgency score, take the highest score from messages
        if v == 0.0 and 'urgency_score' in values:
            return max([msg.urgency_score for msg in values['messages']], default=0.0)
            
        return v
    
    @property
    def newest_message(self) -> Optional[EmailMessage]:
        """Get the newest message in the thread."""
        if not self.messages:
            return None
        return max(self.messages, key=lambda msg: msg.date or datetime.min)
    
    @property
    def oldest_message(self) -> Optional[EmailMessage]:
        """Get the oldest message in the thread."""
        if not self.messages:
            return None
        return min(self.messages, key=lambda msg: msg.date or datetime.max)
    
    @property
    def subject(self) -> str:
        """Get the subject from the newest message."""
        if not self.messages:
            return ""
        # Try to get from the first message (usually has the original subject)
        if self.messages[0].subject:
            return self.messages[0].subject
        # Fall back to newest message
        newest = self.newest_message
        return newest.subject if newest else ""
    
    @property
    def participants(self) -> Set[str]:
        """Get unique email addresses of all participants."""
        result = set()
        for msg in self.messages:
            # Add sender
            if isinstance(msg.from_, EmailAddress):
                result.add(msg.from_.email)
            elif isinstance(msg.from_, list):
                result.update(addr.email for addr in msg.from_)
                
            # Add recipients
            for field in (msg.to, msg.cc, msg.bcc):
                if field:
                    result.update(addr.email for addr in field)
        return result


class GmailSearchQuery(BaseModel):
    """Model for Gmail search query parameters."""
    query: str = "is:unread in:inbox"
    max_results: int = Field(default=50, ge=1, le=500)
    include_spam_trash: bool = False
    label_ids: Optional[List[str]] = None
    page_token: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API request."""
        result = {
            "q": self.query,
            "maxResults": self.max_results,
            "includeSpamTrash": self.include_spam_trash
        }
        if self.label_ids:
            result["labelIds"] = self.label_ids
        if self.page_token:
            result["pageToken"] = self.page_token
        return result


class BatchRequestItem(BaseModel):
    """Model for a single item in a batch request."""
    id: str
    method: str
    endpoint: str
    body: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic config."""
        extra = "allow"


class BatchRequest(BaseModel):
    """Model for a batch request to Gmail API."""
    items: List[BatchRequestItem] = Field(default_factory=list)
    
    def add_item(self, item_id: str, method: str, endpoint: str, 
                body: Optional[Dict[str, Any]] = None,
                params: Optional[Dict[str, Any]] = None) -> None:
        """Add an item to the batch request."""
        self.items.append(BatchRequestItem(
            id=item_id,
            method=method,
            endpoint=endpoint,
            body=body,
            params=params
        ))
