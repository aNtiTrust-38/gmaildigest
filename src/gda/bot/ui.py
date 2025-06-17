"""
UI utility classes for Telegram bot.

This module provides helper classes for generating Telegram UI components
like inline keyboard buttons and formatting messages.
"""

import html
from typing import List, Optional, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
# `telegram.helpers.escape_html` is only available in PTB ≤19.
# To avoid a hard dependency on that private helper, use Python’s
# built-in html.escape which provides equivalent functionality.

MAX_MESSAGE_LENGTH = 4096


class ButtonFactory:
    """
    Factory for creating Telegram inline keyboard buttons.
    """

    @staticmethod
    def create_button(text: str, callback_data: str) -> InlineKeyboardButton:
        """
        Creates a single inline keyboard button with callback data.
        """
        return InlineKeyboardButton(text, callback_data=callback_data)

    @staticmethod
    def create_url_button(text: str, url: str) -> InlineKeyboardButton:
        """
        Creates a single inline keyboard button with a URL.
        """
        return InlineKeyboardButton(text, url=url)

    @staticmethod
    def create_keyboard(
        buttons_layout: List[List[InlineKeyboardButton]],
    ) -> InlineKeyboardMarkup:
        """
        Creates an InlineKeyboardMarkup from a list of lists of buttons.
        """
        return InlineKeyboardMarkup(buttons_layout)


class MessageFormatter:
    """
    Utility for formatting Telegram messages.
    """

    @staticmethod
    def format_message(text: str, parse_mode: Optional[str] = None) -> str:
        """
        Formats a message with a given parse mode.
        """
        # Currently, this just passes through, but can be extended for more complex formatting
        return text

    @staticmethod
    def escape_html(text: str) -> str:
        """
        Escapes HTML special characters in a string.
        """
        if not isinstance(text, str):
            text = str(text)
        # html.escape converts &, <, >, " and ' to HTML-safe sequences.
        # PTB’s helper did the same, so this is a drop-in replacement.
        return html.escape(text, quote=True)

    @staticmethod
    def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> List[str]:
        """
        Splits a long message into multiple chunks to adhere to Telegram's message limit.
        Attempts to split by newline characters first to maintain readability.
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = []
        current_length = 0

        lines = text.split('\n')
        for line in lines:
            # If adding the current line exceeds max_length, start a new chunk
            # +1 for the newline character if it's not the first line in the chunk
            if current_length + len(line) + (1 if current_chunk else 0) > max_length:
                if current_chunk: # Only add if there's content to add
                    chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = len(line)
            else:
                current_chunk.append(line)
                current_length += len(line) + (1 if current_chunk else 0) # Add 1 for newline

        if current_chunk:
            chunks.append('\n'.join(current_chunk))
            
        # Fallback for very long lines that cannot be split by newline
        final_chunks = []
        for chunk in chunks:
            while len(chunk) > max_length:
                final_chunks.append(chunk[:max_length])
                chunk = chunk[max_length:]
            if chunk:
                final_chunks.append(chunk)

        return final_chunks
