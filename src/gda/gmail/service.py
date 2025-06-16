"""
Gmail Service Module for Gmail Digest Assistant v2.0.

This module provides an asynchronous interface for interacting with the Gmail API,
including fetching, parsing, and manipulating emails, with support for batching,
error handling, and all core functionality needed for the application.
"""
import asyncio
import base64
import email
import json
import logging
import re
import time
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from html import unescape
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast
from urllib.parse import quote

import aiohttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest

from gda.auth import AuthManager, AuthError
from gda.config import Settings, get_settings
from gda.gmail.models import (
    BatchRequest,
    EmailAddress,
    EmailAttachment,
    EmailBody,
    EmailHeader,
    EmailLabel,
    EmailMessage,
    EmailThread,
    GmailSearchQuery,
    LabelType,
    MessageImportance,
)

# Configure logger
logger = logging.getLogger(__name__)

# Constants
GMAIL_API_VERSION = "v1"
GMAIL_API_BASE_URL = "https://gmail.googleapis.com"
IMPORTANT_SENDER_LABEL = "Important-Sender"
SYSTEM_LABELS = {
    "INBOX": "INBOX",
    "SENT": "SENT",
    "DRAFT": "DRAFT",
    "TRASH": "TRASH",
    "SPAM": "SPAM",
    "STARRED": "STARRED",
    "IMPORTANT": "IMPORTANT",
    "UNREAD": "UNREAD",
    "CATEGORY_PERSONAL": "CATEGORY_PERSONAL",
    "CATEGORY_SOCIAL": "CATEGORY_SOCIAL",
    "CATEGORY_UPDATES": "CATEGORY_UPDATES",
    "CATEGORY_FORUMS": "CATEGORY_FORUMS",
    "CATEGORY_PROMOTIONS": "CATEGORY_PROMOTIONS",
}


class GmailServiceError(Exception):
    """Base exception for Gmail service errors."""
    pass


class GmailRateLimitError(GmailServiceError):
    """Exception raised when Gmail API rate limit is hit."""
    pass


class GmailBatchError(GmailServiceError):
    """Exception raised when a batch request fails."""
    pass


class GmailService:
    """
    Asynchronous service for interacting with Gmail API.
    
    This class provides methods for fetching, parsing, and manipulating emails,
    with support for batching, error handling, and all core functionality needed
    for the application.
    """
    
    def __init__(
        self,
        auth_manager: AuthManager,
        settings: Optional[Settings] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        batch_size: int = 50,
    ):
        """
        Initialize the Gmail service.
        
        Args:
            auth_manager: Authentication manager for OAuth
            settings: Application settings
            max_retries: Maximum number of retries for API requests
            retry_delay: Base delay between retries (exponential backoff)
            batch_size: Maximum number of operations in a batch request
        """
        self.auth_manager = auth_manager
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.batch_size = batch_size
        
        # Cache for labels and important senders
        self._labels_cache: Dict[str, EmailLabel] = {}
        self._important_senders_cache: Set[str] = set()
        self._labels_cache_expiry = datetime.now()
        self._important_senders_cache_expiry = datetime.now()
        
        # Cache expiry time (1 hour)
        self._cache_expiry_seconds = 3600
        
        # Initialize service (will be created on first use)
        self._service = None
        self._service_created_at = None
        
        logger.debug("Gmail service initialized")
    
    async def _get_service(self):
        """
        Get or create Gmail API service.
        
        Returns:
            Gmail API service instance
        
        Raises:
            AuthError: If authentication fails
            GmailServiceError: If service creation fails
        """
        # Check if service exists and is not expired (refresh every 30 minutes)
        if (
            self._service is not None
            and self._service_created_at is not None
            and (datetime.now() - self._service_created_at).total_seconds() < 1800
        ):
            return self._service
        
        try:
            # Get credentials from auth manager
            credentials = await self.auth_manager.get_credentials()
            
            # Create service in a thread to avoid blocking
            loop = asyncio.get_running_loop()
            service = await loop.run_in_executor(
                None,
                lambda: build(
                    "gmail", GMAIL_API_VERSION, credentials=credentials
                ),
            )
            
            self._service = service
            self._service_created_at = datetime.now()
            return service
            
        except AuthError as e:
            logger.error(f"Authentication error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating Gmail service: {e}")
            raise GmailServiceError(f"Failed to create Gmail service: {e}")
    
    async def _execute_request(
        self, request_fn, *args, retry_count=0, **kwargs
    ):
        """
        Execute a Gmail API request with retry logic.
        
        Args:
            request_fn: Function to execute
            *args: Arguments for the function
            retry_count: Current retry count
            **kwargs: Keyword arguments for the function
            
        Returns:
            API response
            
        Raises:
            GmailRateLimitError: If rate limit is hit and max retries exceeded
            GmailServiceError: If request fails and max retries exceeded
        """
        try:
            # Execute request in a thread to avoid blocking
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, lambda: request_fn(*args, **kwargs).execute()
            )
            
        except HttpError as e:
            status = e.resp.status
            
            # Handle rate limiting
            if status in (403, 429, 500, 503):
                if retry_count < self.max_retries:
                    # Calculate delay with exponential backoff and jitter
                    delay = self.retry_delay * (2 ** retry_count) * (0.5 + 0.5 * (hash(str(time.time())) % 100) / 100)
                    
                    logger.warning(
                        f"Rate limit hit or server error ({status}), "
                        f"retrying in {delay:.2f}s (attempt {retry_count + 1}/{self.max_retries})"
                    )
                    
                    await asyncio.sleep(delay)
                    return await self._execute_request(
                        request_fn, *args, retry_count=retry_count + 1, **kwargs
                    )
                else:
                    logger.error(
                        f"Rate limit hit or server error ({status}), "
                        f"max retries ({self.max_retries}) exceeded"
                    )
                    raise GmailRateLimitError(
                        f"Gmail API rate limit hit, max retries exceeded: {e}"
                    )
            
            # Other HTTP errors
            logger.error(f"Gmail API HTTP error: {e}")
            raise GmailServiceError(f"Gmail API request failed: {e}")
            
        except Exception as e:
            if retry_count < self.max_retries:
                delay = self.retry_delay * (2 ** retry_count)
                logger.warning(
                    f"Gmail API request failed, retrying in {delay:.2f}s "
                    f"(attempt {retry_count + 1}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(delay)
                return await self._execute_request(
                    request_fn, *args, retry_count=retry_count + 1, **kwargs
                )
            else:
                logger.error(f"Gmail API request failed, max retries exceeded: {e}")
                raise GmailServiceError(f"Gmail API request failed: {e}")
    
    async def _execute_batch(
        self, batch_request: BatchRequest, retry_count=0
    ) -> Dict[str, Any]:
        """
        Execute a batch request to Gmail API.
        
        Args:
            batch_request: Batch request to execute
            retry_count: Current retry count
            
        Returns:
            Dictionary mapping request IDs to responses
            
        Raises:
            GmailBatchError: If batch request fails
        """
        try:
            service = await self._get_service()
            
            # Create a batch request
            batch = service.new_batch_http_request()
            
            # Results dictionary
            results: Dict[str, Any] = {}
            
            # Create callback function to store results
            def callback(request_id, response, exception):
                if exception:
                    results[request_id] = {"error": str(exception)}
                else:
                    results[request_id] = response
            
            # Add requests to batch
            for item in batch_request.items:
                # Get the API method
                parts = item.endpoint.strip("/").split("/")
                if len(parts) < 2:
                    raise GmailBatchError(f"Invalid endpoint: {item.endpoint}")
                
                resource_name = parts[0]
                method_name = parts[1]
                
                # Get the resource
                resource = getattr(service.users(), resource_name)()
                
                # Get the method
                method = getattr(resource, method_name)
                
                # Create the request
                request_args = {}
                if item.params:
                    request_args.update(item.params)
                
                if item.method.upper() == "GET":
                    request = method(**request_args)
                else:
                    request = method(body=item.body, **request_args)
                
                # Add to batch
                batch.add(request, callback=callback, request_id=item.id)
            
            # Execute batch in a thread
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, batch.execute)
            
            return results
            
        except HttpError as e:
            status = e.resp.status
            
            # Handle rate limiting
            if status in (403, 429, 500, 503):
                if retry_count < self.max_retries:
                    delay = self.retry_delay * (2 ** retry_count)
                    logger.warning(
                        f"Rate limit hit or server error ({status}), "
                        f"retrying batch in {delay:.2f}s "
                        f"(attempt {retry_count + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    return await self._execute_batch(
                        batch_request, retry_count=retry_count + 1
                    )
                else:
                    logger.error(
                        f"Rate limit hit or server error ({status}), "
                        f"max retries ({self.max_retries}) exceeded for batch"
                    )
                    raise GmailRateLimitError(
                        f"Gmail API rate limit hit for batch, max retries exceeded: {e}"
                    )
            
            # Other HTTP errors
            logger.error(f"Gmail API HTTP error in batch: {e}")
            raise GmailBatchError(f"Gmail API batch request failed: {e}")
            
        except Exception as e:
            if retry_count < self.max_retries:
                delay = self.retry_delay * (2 ** retry_count)
                logger.warning(
                    f"Gmail API batch request failed, retrying in {delay:.2f}s "
                    f"(attempt {retry_count + 1}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(delay)
                return await self._execute_batch(
                    batch_request, retry_count=retry_count + 1
                )
            else:
                logger.error(f"Gmail API batch request failed, max retries exceeded: {e}")
                raise GmailBatchError(f"Gmail API batch request failed: {e}")
    
    async def list_labels(self, force_refresh: bool = False) -> List[EmailLabel]:
        """
        List all Gmail labels.
        
        Args:
            force_refresh: Force refresh of labels cache
            
        Returns:
            List of labels
            
        Raises:
            GmailServiceError: If request fails
        """
        # Check cache first
        if (
            not force_refresh
            and self._labels_cache
            and (datetime.now() - self._labels_cache_expiry).total_seconds()
            < self._cache_expiry_seconds
        ):
            return list(self._labels_cache.values())
        
        try:
            service = await self._get_service()
            response = await self._execute_request(
                service.users().labels().list, userId="me"
            )
            
            labels = []
            for label_data in response.get("labels", []):
                label = EmailLabel(
                    id=label_data["id"],
                    name=label_data["name"],
                    type=LabelType.SYSTEM
                    if label_data["type"] == "system"
                    else LabelType.USER,
                    message_list_visibility=label_data.get("messageListVisibility"),
                    label_list_visibility=label_data.get("labelListVisibility"),
                    color=label_data.get("color"),
                )
                labels.append(label)
                self._labels_cache[label.id] = label
            
            self._labels_cache_expiry = datetime.now()
            return labels
            
        except Exception as e:
            logger.error(f"Error listing labels: {e}")
            raise GmailServiceError(f"Failed to list labels: {e}")
    
    async def get_label(self, label_id: str) -> Optional[EmailLabel]:
        """
        Get a label by ID.
        
        Args:
            label_id: Label ID
            
        Returns:
            Label or None if not found
            
        Raises:
            GmailServiceError: If request fails
        """
        # Check cache first
        if label_id in self._labels_cache:
            return self._labels_cache[label_id]
        
        # Refresh labels cache
        await self.list_labels(force_refresh=True)
        
        # Check cache again
        return self._labels_cache.get(label_id)
    
    async def create_label(
        self, name: str, visibility: Optional[str] = None
    ) -> EmailLabel:
        """
        Create a new Gmail label.
        
        Args:
            name: Label name
            visibility: Label visibility
            
        Returns:
            Created label
            
        Raises:
            GmailServiceError: If request fails
        """
        try:
            service = await self._get_service()
            
            # Check if label already exists
            existing_labels = await self.list_labels()
            for label in existing_labels:
                if label.name == name:
                    return label
            
            # Create label
            label_data = {"name": name}
            if visibility:
                label_data["messageListVisibility"] = visibility
                label_data["labelListVisibility"] = visibility
            
            response = await self._execute_request(
                service.users().labels().create, userId="me", body=label_data
            )
            
            # Create label object
            label = EmailLabel(
                id=response["id"],
                name=response["name"],
                type=LabelType.USER,
                message_list_visibility=response.get("messageListVisibility"),
                label_list_visibility=response.get("labelListVisibility"),
            )
            
            # Update cache
            self._labels_cache[label.id] = label
            
            return label
            
        except Exception as e:
            logger.error(f"Error creating label '{name}': {e}")
            raise GmailServiceError(f"Failed to create label: {e}")
    
    async def get_important_senders(self, force_refresh: bool = False) -> Set[str]:
        """
        Get set of important sender email addresses.
        
        Args:
            force_refresh: Force refresh of important senders cache
            
        Returns:
            Set of important sender email addresses
            
        Raises:
            GmailServiceError: If request fails
        """
        # Check cache first
        if (
            not force_refresh
            and self._important_senders_cache
            and (datetime.now() - self._important_senders_cache_expiry).total_seconds()
            < self._cache_expiry_seconds
        ):
            return self._important_senders_cache
        
        try:
            # Get or create Important-Sender label
            important_label = None
            try:
                labels = await self.list_labels()
                for label in labels:
                    if label.name == IMPORTANT_SENDER_LABEL:
                        important_label = label
                        break
                
                if not important_label:
                    important_label = await self.create_label(IMPORTANT_SENDER_LABEL)
            except Exception as e:
                logger.warning(f"Error getting/creating Important-Sender label: {e}")
            
            if not important_label:
                return set()
            
            # Search for emails with Important-Sender label
            query = GmailSearchQuery(
                query=f"label:{IMPORTANT_SENDER_LABEL}",
                max_results=100,
            )
            
            messages = await self.search_messages(query)
            
            # Extract unique sender email addresses
            senders = set()
            for message in messages:
                if message.sender_address:
                    senders.add(message.sender_address)
            
            # Update cache
            self._important_senders_cache = senders
            self._important_senders_cache_expiry = datetime.now()
            
            return senders
            
        except Exception as e:
            logger.error(f"Error getting important senders: {e}")
            raise GmailServiceError(f"Failed to get important senders: {e}")
    
    async def mark_sender_important(
        self, email_address: str, important: bool = True
    ) -> bool:
        """
        Mark or unmark a sender as important.
        
        Args:
            email_address: Sender email address
            important: True to mark as important, False to unmark
            
        Returns:
            True if successful
            
        Raises:
            GmailServiceError: If request fails
        """
        try:
            # Get or create Important-Sender label
            important_label = None
            try:
                labels = await self.list_labels()
                for label in labels:
                    if label.name == IMPORTANT_SENDER_LABEL:
                        important_label = label
                        break
                
                if not important_label:
                    important_label = await self.create_label(IMPORTANT_SENDER_LABEL)
            except Exception as e:
                logger.error(f"Error getting/creating Important-Sender label: {e}")
                raise GmailServiceError(f"Failed to get/create Important-Sender label: {e}")
            
            if important:
                # Mark as important
                
                # Search for a recent email from this sender
                query = GmailSearchQuery(
                    query=f"from:{email_address}",
                    max_results=1,
                )
                
                messages = await self.search_messages(query)
                
                if messages:
                    # Add Important-Sender label to the message
                    message = messages[0]
                    await self.modify_message(
                        message.id,
                        add_label_ids=[important_label.id],
                    )
                else:
                    # No messages found, create a dummy message
                    logger.warning(
                        f"No messages found from {email_address}, "
                        "can't mark as important without a message"
                    )
                    return False
                
                # Update cache
                self._important_senders_cache.add(email_address)
                
            else:
                # Unmark as important
                
                # Search for emails from this sender with Important-Sender label
                query = GmailSearchQuery(
                    query=f"from:{email_address} label:{IMPORTANT_SENDER_LABEL}",
                    max_results=10,
                )
                
                messages = await self.search_messages(query)
                
                # Remove Important-Sender label from all messages
                for message in messages:
                    await self.modify_message(
                        message.id,
                        remove_label_ids=[important_label.id],
                    )
                
                # Update cache
                self._important_senders_cache.discard(email_address)
            
            return True
            
        except Exception as e:
            logger.error(f"Error marking sender {email_address} as important: {e}")
            raise GmailServiceError(f"Failed to mark sender as important: {e}")
    
    async def is_sender_important(self, email_address: str) -> bool:
        """
        Check if a sender is marked as important.
        
        Args:
            email_address: Sender email address
            
        Returns:
            True if sender is important
            
        Raises:
            GmailServiceError: If request fails
        """
        important_senders = await self.get_important_senders()
        return email_address in important_senders
    
    async def search_messages(
        self, query: GmailSearchQuery
    ) -> List[EmailMessage]:
        """
        Search for messages using a query.
        
        Args:
            query: Search query parameters
            
        Returns:
            List of messages matching the query
            
        Raises:
            GmailServiceError: If request fails
        """
        try:
            service = await self._get_service()
            
            # Execute search
            response = await self._execute_request(
                service.users().messages().list,
                userId="me",
                **query.to_dict(),
            )
            
            messages = []
            message_ids = []
            
            # Extract message IDs
            for item in response.get("messages", []):
                message_ids.append(item["id"])
            
            # Fetch messages in batches
            if message_ids:
                batch_size = self.settings.gmail.batch_size
                for i in range(0, len(message_ids), batch_size):
                    batch_ids = message_ids[i:i + batch_size]
                    batch_messages = await self.batch_get_messages(batch_ids)
                    messages.extend(batch_messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error searching messages with query {query.query}: {e}")
            raise GmailServiceError(f"Failed to search messages: {e}")
    
    async def get_message(self, message_id: str) -> EmailMessage:
        """
        Get a message by ID.
        
        Args:
            message_id: Message ID
            
        Returns:
            Message
            
        Raises:
            GmailServiceError: If request fails
        """
        try:
            service = await self._get_service()
            
            # Get message
            response = await self._execute_request(
                service.users().messages().get,
                userId="me",
                id=message_id,
                format="full",
            )
            
            # Parse message
            return await self._parse_message(response)
            
        except Exception as e:
            logger.error(f"Error getting message {message_id}: {e}")
            raise GmailServiceError(f"Failed to get message: {e}")
    
    async def batch_get_messages(self, message_ids: List[str]) -> List[EmailMessage]:
        """
        Get multiple messages by ID in a batch.
        
        Args:
            message_ids: List of message IDs
            
        Returns:
            List of messages
            
        Raises:
            GmailServiceError: If request fails
        """
        if not message_ids:
            return []
        
        try:
            # Create batch request
            batch_request = BatchRequest()
            
            for message_id in message_ids:
                batch_request.add_item(
                    item_id=message_id,
                    method="GET",
                    endpoint="messages/get",
                    params={"userId": "me", "id": message_id, "format": "full"},
                )
            
            # Execute batch
            results = await self._execute_batch(batch_request)
            
            # Parse messages
            messages = []
            for message_id, result in results.items():
                if "error" in result:
                    logger.warning(f"Error getting message {message_id}: {result['error']}")
                    continue
                
                try:
                    message = await self._parse_message(result)
                    messages.append(message)
                except Exception as e:
                    logger.warning(f"Error parsing message {message_id}: {e}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Error batch getting messages: {e}")
            raise GmailServiceError(f"Failed to batch get messages: {e}")
    
    async def get_thread(self, thread_id: str) -> EmailThread:
        """
        Get a thread by ID.
        
        Args:
            thread_id: Thread ID
            
        Returns:
            Thread
            
        Raises:
            GmailServiceError: If request fails
        """
        try:
            service = await self._get_service()
            
            # Get thread
            response = await self._execute_request(
                service.users().threads().get,
                userId="me",
                id=thread_id,
                format="full",
            )
            
            # Parse thread
            return await self._parse_thread(response)
            
        except Exception as e:
            logger.error(f"Error getting thread {thread_id}: {e}")
            raise GmailServiceError(f"Failed to get thread: {e}")
    
    async def batch_get_threads(self, thread_ids: List[str]) -> List[EmailThread]:
        """
        Get multiple threads by ID in a batch.
        
        Args:
            thread_ids: List of thread IDs
            
        Returns:
            List of threads
            
        Raises:
            GmailServiceError: If request fails
        """
        if not thread_ids:
            return []
        
        try:
            # Create batch request
            batch_request = BatchRequest()
            
            for thread_id in thread_ids:
                batch_request.add_item(
                    item_id=thread_id,
                    method="GET",
                    endpoint="threads/get",
                    params={"userId": "me", "id": thread_id, "format": "full"},
                )
            
            # Execute batch
            results = await self._execute_batch(batch_request)
            
            # Parse threads
            threads = []
            for thread_id, result in results.items():
                if "error" in result:
                    logger.warning(f"Error getting thread {thread_id}: {result['error']}")
                    continue
                
                try:
                    thread = await self._parse_thread(result)
                    threads.append(thread)
                except Exception as e:
                    logger.warning(f"Error parsing thread {thread_id}: {e}")
            
            return threads
            
        except Exception as e:
            logger.error(f"Error batch getting threads: {e}")
            raise GmailServiceError(f"Failed to batch get threads: {e}")
    
    async def search_threads(
        self, query: GmailSearchQuery
    ) -> List[EmailThread]:
        """
        Search for threads using a query.
        
        Args:
            query: Search query parameters
            
        Returns:
            List of threads matching the query
            
        Raises:
            GmailServiceError: If request fails
        """
        try:
            service = await self._get_service()
            
            # Execute search
            response = await self._execute_request(
                service.users().threads().list,
                userId="me",
                **query.to_dict(),
            )
            
            threads = []
            thread_ids = []
            
            # Extract thread IDs
            for item in response.get("threads", []):
                thread_ids.append(item["id"])
            
            # Fetch threads in batches
            if thread_ids:
                batch_size = self.settings.gmail.batch_size
                for i in range(0, len(thread_ids), batch_size):
                    batch_ids = thread_ids[i:i + batch_size]
                    batch_threads = await self.batch_get_threads(batch_ids)
                    threads.extend(batch_threads)
            
            return threads
            
        except Exception as e:
            logger.error(f"Error searching threads with query {query.query}: {e}")
            raise GmailServiceError(f"Failed to search threads: {e}")
    
    async def modify_message(
        self,
        message_id: str,
        add_label_ids: Optional[List[str]] = None,
        remove_label_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        Modify a message's labels.
        
        Args:
            message_id: Message ID
            add_label_ids: Labels to add
            remove_label_ids: Labels to remove
            
        Returns:
            True if successful
            
        Raises:
            GmailServiceError: If request fails
        """
        try:
            service = await self._get_service()
            
            # Create request body
            body = {}
            if add_label_ids:
                body["addLabelIds"] = add_label_ids
            if remove_label_ids:
                body["removeLabelIds"] = remove_label_ids
            
            # Execute request
            await self._execute_request(
                service.users().messages().modify,
                userId="me",
                id=message_id,
                body=body,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error modifying message {message_id}: {e}")
            raise GmailServiceError(f"Failed to modify message: {e}")
    
    async def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a message as read.
        
        Args:
            message_id: Message ID
            
        Returns:
            True if successful
            
        Raises:
            GmailServiceError: If request fails
        """
        return await self.modify_message(
            message_id,
            remove_label_ids=[SYSTEM_LABELS["UNREAD"]],
        )
    
    async def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark a message as unread.
        
        Args:
            message_id: Message ID
            
        Returns:
            True if successful
            
        Raises:
            GmailServiceError: If request fails
        """
        return await self.modify_message(
            message_id,
            add_label_ids=[SYSTEM_LABELS["UNREAD"]],
        )
    
    async def archive_message(self, message_id: str) -> bool:
        """
        Archive a message (remove from inbox).
        
        Args:
            message_id: Message ID
            
        Returns:
            True if successful
            
        Raises:
            GmailServiceError: If request fails
        """
        return await self.modify_message(
            message_id,
            remove_label_ids=[SYSTEM_LABELS["INBOX"]],
        )
    
    async def mark_as_read_and_archive(self, message_id: str) -> bool:
        """
        Mark a message as read and archive it.
        
        Args:
            message_id: Message ID
            
        Returns:
            True if successful
            
        Raises:
            GmailServiceError: If request fails
        """
        return await self.modify_message(
            message_id,
            remove_label_ids=[SYSTEM_LABELS["UNREAD"], SYSTEM_LABELS["INBOX"]],
        )
    
    async def forward_email(
        self, message_id: str, to_address: str, subject: Optional[str] = None
    ) -> bool:
        """
        Forward an email to another address.
        
        Args:
            message_id: ID of the message to forward
            to_address: Email address to forward to
            subject: Optional subject for the forwarded email
            
        Returns:
            True if successful
            
        Raises:
            GmailServiceError: If request fails
        """
        try:
            # Get the original message
            message = await self.get_message(message_id)
            
            # Create forward subject
            if subject is None:
                subject = f"Fwd: {message.subject}"
            
            # Create forward body
            body = (
                f"---------- Forwarded message ----------\n"
                f"From: {message.from_ if message.from_ else 'Unknown'}\n"
                f"Date: {message.date.isoformat() if message.date else 'Unknown'}\n"
                f"Subject: {message.subject}\n"
                f"To: {', '.join(str(addr) for addr in message.to) if message.to else 'Unknown'}\n\n"
                f"{message.plain_body}"
            )
            
            # Create raw message
            msg = email.message.EmailMessage()
            msg["To"] = to_address
            msg["Subject"] = subject
            msg.set_content(body)
            
            # Encode and send
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            
            service = await self._get_service()
            await self._execute_request(
                service.users().messages().send,
                userId="me",
                body={"raw": raw},
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error forwarding message {message_id}: {e}")
            raise GmailServiceError(f"Failed to forward message: {e}")
    
    async def _parse_message(self, message_data: Dict[str, Any]) -> EmailMessage:
        """
        Parse a Gmail API message into an EmailMessage object.
        
        Args:
            message_data: Raw message data from Gmail API
            
        Returns:
            Parsed EmailMessage
        """
        # Extract basic info
        message_id = message_data["id"]
        thread_id = message_data["threadId"]
        labels = message_data.get("labelIds", [])
        
        # Extract headers
        headers = []
        header_dict = {}
        for header in message_data["payload"]["headers"]:
            name = header["name"]
            value = header["value"]
            headers.append(EmailHeader(name=name, value=value))
            header_dict[name.lower()] = value
        
        # Extract subject
        subject = header_dict.get("subject", "")
        
        # Extract addresses
        from_addr = self._parse_email_address(header_dict.get("from", ""))
        to_addrs = self._parse_email_addresses(header_dict.get("to", ""))
        cc_addrs = self._parse_email_addresses(header_dict.get("cc", ""))
        bcc_addrs = self._parse_email_addresses(header_dict.get("bcc", ""))
        reply_to_addrs = self._parse_email_addresses(header_dict.get("reply-to", ""))
        
        # Extract date
        date = None
        if "date" in header_dict:
            try:
                date = parsedate_to_datetime(header_dict["date"])
            except Exception:
                pass
        
        # Extract body and attachments
        body, attachments = await self._parse_payload(message_data["payload"])
        
        # Create message object
        message = EmailMessage(
            id=message_id,
            thread_id=thread_id,
            history_id=message_data.get("historyId"),
            subject=subject,
            from_=from_addr,
            to=to_addrs,
            cc=cc_addrs,
            bcc=bcc_addrs,
            reply_to=reply_to_addrs,
            body=body,
            snippet=message_data.get("snippet", ""),
            attachments=attachments,
            date=date,
            labels=labels,
            headers=headers,
            is_unread=SYSTEM_LABELS["UNREAD"] in labels,
            is_starred=SYSTEM_LABELS["STARRED"] in labels,
            is_draft=SYSTEM_LABELS["DRAFT"] in labels,
            is_sent=SYSTEM_LABELS["SENT"] in labels,
            is_inbox=SYSTEM_LABELS["INBOX"] in labels,
            is_trash=SYSTEM_LABELS["TRASH"] in labels,
            is_spam=SYSTEM_LABELS["SPAM"] in labels,
        )
        
        # Set importance based on labels and important senders
        if SYSTEM_LABELS["IMPORTANT"] in labels:
            message.importance = MessageImportance.HIGH
        
        # Check if sender is in important senders cache
        if message.sender_address and message.sender_address in self._important_senders_cache:
            message.importance = MessageImportance.IMPORTANT_SENDER
        
        return message
    
    async def _parse_thread(self, thread_data: Dict[str, Any]) -> EmailThread:
        """
        Parse a Gmail API thread into an EmailThread object.
        
        Args:
            thread_data: Raw thread data from Gmail API
            
        Returns:
            Parsed EmailThread
        """
        # Extract basic info
        thread_id = thread_data["id"]
        history_id = thread_data.get("historyId")
        
        # Parse messages
        messages = []
        for message_data in thread_data.get("messages", []):
            try:
                message = await self._parse_message(message_data)
                messages.append(message)
            except Exception as e:
                logger.warning(f"Error parsing message in thread {thread_id}: {e}")
        
        # Sort messages by date
        messages.sort(key=lambda msg: msg.date or datetime.min)
        
        # Extract labels (union of all message labels)
        labels = set()
        for message in messages:
            labels.update(message.labels)
        
        # Create thread object
        thread = EmailThread(
            id=thread_id,
            history_id=history_id,
            messages=messages,
            snippet=thread_data.get("snippet", ""),
            labels=list(labels),
            is_unread=any(msg.is_unread for msg in messages),
        )
        
        return thread
    
    async def _parse_payload(
        self, payload: Dict[str, Any], parent_type: str = ""
    ) -> Tuple[EmailBody, List[EmailAttachment]]:
        """
        Parse a MIME payload into body and attachments.
        
        Args:
            payload: MIME payload from Gmail API
            parent_type: MIME type of parent part
            
        Returns:
            Tuple of (body, attachments)
        """
        mime_type = payload.get("mimeType", "")
        
        # Initialize body and attachments
        body = EmailBody()
        attachments = []
        
        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                part_body, part_attachments = await self._parse_payload(part, mime_type)
                
                # Merge bodies
                if part_body.plain_text and not body.plain_text:
                    body.plain_text = part_body.plain_text
                elif part_body.plain_text:
                    body.plain_text = f"{body.plain_text}\n\n{part_body.plain_text}"
                
                if part_body.html and not body.html:
                    body.html = part_body.html
                elif part_body.html:
                    body.html = f"{body.html}\n\n{part_body.html}"
                
                # Add attachments
                attachments.extend(part_attachments)
                
        elif "body" in payload:
            # Single part message
            body_data = payload["body"]
            
            if "data" in body_data:
                # Decode body data
                data = base64.urlsafe_b64decode(body_data["data"]).decode("utf-8", errors="replace")
                
                if mime_type == "text/plain":
                    body.plain_text = data
                elif mime_type == "text/html":
                    body.html = data
                    
            elif "attachmentId" in body_data:
                # This is an attachment
                attachment = EmailAttachment(
                    attachment_id=body_data["attachmentId"],
                    filename=payload.get("filename", ""),
                    mime_type=mime_type,
                    size=body_data.get("size", 0),
                    content_id=payload.get("headers", {}).get("Content-ID", None),
                    inline="inline" in payload.get("disposition", "").lower(),
                )
                attachments.append(attachment)
        
        return body, attachments
    
    def _parse_email_address(self, address_str: str) -> Optional[EmailAddress]:
        """
        Parse an email address string into an EmailAddress object.
        
        Args:
            address_str: Email address string
            
        Returns:
            EmailAddress object or None if invalid
        """
        if not address_str:
            return None
        
        # Parse address
        name, email_addr = parseaddr(address_str)
        
        # Decode name if needed
        if name:
            try:
                decoded_parts = []
                for part, encoding in decode_header(name):
                    if isinstance(part, bytes):
                        if encoding:
                            decoded_parts.append(part.decode(encoding, errors="replace"))
                        else:
                            decoded_parts.append(part.decode("utf-8", errors="replace"))
                    else:
                        decoded_parts.append(part)
                name = "".join(decoded_parts)
            except Exception:
                pass
        
        if not email_addr:
            return None
        
        try:
            return EmailAddress(name=name or None, email=email_addr)
        except Exception:
            # Fall back to just using the raw string as email
            try:
                return EmailAddress(email=address_str)
            except Exception:
                return None
    
    def _parse_email_addresses(self, addresses_str: str) -> List[EmailAddress]:
        """
        Parse a comma-separated list of email addresses.
        
        Args:
            addresses_str: Comma-separated email addresses
            
        Returns:
            List of EmailAddress objects
        """
        if not addresses_str:
            return []
        
        result = []
        
        # Split by comma and parse each address
        for addr_str in addresses_str.split(","):
            addr = self._parse_email_address(addr_str.strip())
            if addr:
                result.append(addr)
        
        return result
