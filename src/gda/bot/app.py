"""
Telegram bot application for Gmail Digest Assistant v2.

This module provides the BotApp class that initializes and runs the Telegram bot,
registers command handlers, and manages the bot lifecycle.
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from gda.auth import AuthManager
from gda.config import Settings

# Configure logger
logger = logging.getLogger(__name__)


class BotApp:
    """
    Main Telegram bot application for Gmail Digest Assistant.
    
    This class initializes the bot, registers command handlers, and manages the
    bot lifecycle. It serves as the entry point for the Telegram bot functionality.
    """
    
    def __init__(self, settings: Settings, auth_manager: AuthManager):
        """
        Initialize the bot application.
        
        Args:
            settings: Application settings
            auth_manager: Authentication manager for OAuth
        """
        self.settings = settings
        self.auth_manager = auth_manager
        self.bot_token = settings.telegram.bot_token.get_secret_value()
        self.allowed_chat_ids = settings.telegram.allowed_chat_ids
        
        # Initialize bot application
        self.application = Application.builder().token(self.bot_token).build()
        
        # Command registry
        self.commands = {}
        
        # User data store
        self.user_data = {}
        
        # Register command handlers
        self._register_handlers()
        
        logger.info("Bot application initialized")
    
    def _register_handlers(self) -> None:
        """Register command and callback handlers."""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("digest", self._handle_digest))
        self.application.add_handler(CommandHandler("settings", self._handle_settings))
        self.application.add_handler(CommandHandler("reauthorize", self._handle_reauthorize))
        self.application.add_handler(CommandHandler("version", self._handle_version))
        
        # Callback query handler for buttons
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
        
        # Error handler
        self.application.add_error_handler(self._handle_error)
        
        logger.debug("Command handlers registered")
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        chat_id = update.effective_chat.id
        
        # Check if chat is allowed
        if not self._is_chat_allowed(chat_id):
            await update.message.reply_text(
                "⚠️ You are not authorized to use this bot. "
                "Please contact the administrator."
            )
            return
        
        # Initialize user data
        self.user_data[chat_id] = {
            "last_digest": None,
            "settings": {
                "digest_interval": self.settings.telegram.default_digest_interval_hours,
                "notifications_enabled": True,
            }
        }
        
        # Send welcome message
        await update.message.reply_text(
            f"👋 Welcome to Gmail Digest Assistant v{self.settings.app.version}!\n\n"
            "I'll help you manage your Gmail inbox with summarized digests "
            "and smart notifications.\n\n"
            "Use /help to see available commands."
        )
        
        # Start periodic jobs
        await self._start_jobs(chat_id, context)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = (
            "📚 *Gmail Digest Assistant Commands*\n\n"
            "/start - Initialize the bot and start scheduled digests\n"
            "/digest - Get immediate email digest\n"
            "/settings - View and change settings\n"
            "/reauthorize - Force Google reauthorization\n"
            "/version - Show version information\n"
            "/help - Show this help message\n\n"
            "Use the buttons below messages for quick actions."
        )
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _handle_digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /digest command."""
        chat_id = update.effective_chat.id
        
        # Check if chat is allowed
        if not self._is_chat_allowed(chat_id):
            return
        
        await update.message.reply_text(
            "🔄 Generating digest...\n\n"
            "This feature is being implemented. Please check back soon!"
        )
    
    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command."""
        chat_id = update.effective_chat.id
        
        # Check if chat is allowed
        if not self._is_chat_allowed(chat_id):
            return
        
        # Get user settings
        user_settings = self.user_data.get(chat_id, {}).get("settings", {})
        
        settings_text = (
            "⚙️ *Settings*\n\n"
            f"Digest interval: {user_settings.get('digest_interval', 2)} hours\n"
            f"Notifications: {'Enabled' if user_settings.get('notifications_enabled', True) else 'Disabled'}\n\n"
            "This feature is being expanded. More options coming soon!"
        )
        
        await update.message.reply_text(settings_text, parse_mode="Markdown")
    
    async def _handle_reauthorize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reauthorize command."""
        chat_id = update.effective_chat.id
        
        # Check if chat is allowed
        if not self._is_chat_allowed(chat_id):
            return
        
        await update.message.reply_text(
            "🔄 Starting Google re-authorization flow...\n"
            "A browser window will open shortly."
        )
        
        try:
            # Run reauthorization in background
            credentials = await self.auth_manager.force_reauthorize()
            await update.message.reply_text(
                "✅ Authorization complete! You can resume using the bot."
            )
            logger.info(f"User {chat_id} successfully re-authorized Google account")
        except Exception as e:
            logger.error(f"Reauthorization failed: {e}", exc_info=True)
            await update.message.reply_text(
                "⚠️ Reauthorization failed. Please try again later or check logs."
            )
    
    async def _handle_version(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /version command."""
        version_text = (
            f"📱 *Gmail Digest Assistant v{self.settings.app.version}*\n\n"
            f"Environment: {self.settings.app.environment.value}\n"
            f"Anthropic API: {'Configured' if self.settings.summary.anthropic_api_key else 'Not configured'}\n"
            f"OpenAI API: {'Configured' if self.settings.summary.openai_api_key else 'Not configured'}\n"
        )
        
        await update.message.reply_text(version_text, parse_mode="Markdown")
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        await query.answer()
        
        # Handle different callback data
        data = query.data
        if data.startswith("digest_"):
            # Handle digest-related callbacks
            pass
        elif data.startswith("settings_"):
            # Handle settings-related callbacks
            pass
        else:
            logger.warning(f"Unknown callback data: {data}")
    
    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in the dispatcher."""
        logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)
        
        # Send error message to user if possible
        if update and isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Sorry, an error occurred. Please try again later."
            )
    
    async def _start_jobs(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start periodic jobs for a chat."""
        # Get user settings
        user_settings = self.user_data.get(chat_id, {}).get("settings", {})
        
        # Schedule digest job
        digest_interval = user_settings.get(
            "digest_interval", 
            self.settings.telegram.default_digest_interval_hours
        )
        
        # Remove existing jobs for this chat
        current_jobs = context.job_queue.get_jobs_by_name(f"digest_{chat_id}")
        for job in current_jobs:
            job.schedule_removal()
        
        # Schedule new digest job
        context.job_queue.run_repeating(
            self._send_periodic_digest,
            interval=digest_interval * 3600,  # Convert hours to seconds
            first=60,  # First run after 60 seconds
            chat_id=chat_id,
            name=f"digest_{chat_id}",
            data={"chat_id": chat_id}
        )
        
        # Schedule important emails check job
        check_interval = self.settings.telegram.check_interval_minutes
        context.job_queue.run_repeating(
            self._check_important_emails,
            interval=check_interval * 60,  # Convert minutes to seconds
            first=120,  # First run after 120 seconds
            chat_id=chat_id,
            name=f"important_{chat_id}",
            data={"chat_id": chat_id}
        )
        
        logger.debug(f"Started periodic jobs for chat {chat_id}")
    
    async def _send_periodic_digest(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send periodic digest to user."""
        job = context.job
        chat_id = job.data["chat_id"]
        
        # Check if chat is allowed
        if not self._is_chat_allowed(chat_id):
            return
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="🔄 This is a placeholder for the periodic digest.\n\n"
                 "Full implementation coming soon!"
        )
    
    async def _check_important_emails(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Check for important emails."""
        job = context.job
        chat_id = job.data["chat_id"]
        
        # Check if chat is allowed
        if not self._is_chat_allowed(chat_id):
            return
        
        # Get user settings
        user_settings = self.user_data.get(chat_id, {}).get("settings", {})
        
        # Skip if notifications are disabled
        if not user_settings.get("notifications_enabled", True):
            return
        
        # In a real implementation, this would check for important emails
        # and send notifications if any are found
        pass
    
    def _is_chat_allowed(self, chat_id: int) -> bool:
        """Check if a chat is allowed to use the bot."""
        if self.allowed_chat_ids is None:
            # No restrictions
            return True
        
        return chat_id in self.allowed_chat_ids
    
    async def run(self) -> None:
        """Run the bot application."""
        # Prevent double-start if a previous instance didn’t shut down cleanly
        if getattr(self.application.updater, "running", False):
            logger.warning("Updater already running – skipping new start.")
            return

        # Initialise & start dispatcher / aiohttp pool
        await self.application.initialize()
        await self.application.start()

        try:
            logger.info("Bot started – press Ctrl+C to stop.")

            # Start polling in the background
            await self.application.updater.start_polling()

            # Wait for signal (SIGINT/SIGTERM) instead of .idle() which would
            # raise if updater already running elsewhere.  PTB ≥20 exposes the
            # coroutine `wait_for_stop()` for this purpose.
            await self.application.updater.wait_for_stop()

        finally:
            # Graceful shutdown
            if not self.application.updater.running:
                logger.debug("Updater already stopped.")
            else:
                await self.application.updater.stop()

            await self.application.stop()
            await self.application.shutdown()

            logger.info("Bot stopped cleanly.")
