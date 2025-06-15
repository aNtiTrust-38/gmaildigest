"""
Telegram Bot Module for Gmail Digest Assistant
"""
import os
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext,
    JobQueue,
    CallbackQueryHandler
)
import dateparser
import pytz
from dotenv import load_dotenv
from .gmail_service import GmailService
from .auth import GmailAuthenticator
from .summarization import summarize_email, estimate_reading_time, robust_summarize

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def html_escape(text):
    if not isinstance(text, str):
        text = str(text)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

MAX_MESSAGE_LENGTH = 4096

def split_message(text, max_length=MAX_MESSAGE_LENGTH):
    lines = text.split('\n')
    chunks = []
    current = ''
    for line in lines:
        if len(current) + len(line) + 1 > max_length:
            chunks.append(current)
            current = line
        else:
            if current:
                current += '\n'
            current += line
    if current:
        chunks.append(current)
    return chunks

def clean_summary(text):
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove image/file references (common patterns)
    text = re.sub(r'\[image:.*?\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[cid:.*?\]', '', text, flags=re.IGNORECASE)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def urgency_marker(urgency):
    if urgency == "Important Sender":
        return "🔴 Urgent"
    if urgency.startswith("Urgent"):
        return "🔴 Urgent"
    return "🟢 Normal"

class GmailDigestBot:
    """Telegram bot for Gmail digest notifications"""
    
    def __init__(self):
        """Initialize the bot with configuration"""
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
            
        # Initialize Gmail service
        self.auth = GmailAuthenticator()
        credentials = self.auth.get_credentials()
        self.gmail_service = GmailService(credentials)
        
        # Store chat_id -> settings mapping
        self.user_settings: Dict[int, Dict[str, Any]] = {}
        
        # Forwarding address
        self.forward_address = os.getenv('FORWARD_EMAIL', 'kai@peacefamily.us')
        
        # Check interval for important emails (minutes)
        self.check_interval_minutes = int(os.getenv('CHECK_INTERVAL_MINUTES', '15'))
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        chat_id = update.effective_chat.id
        
        # Initialize user settings with defaults
        self.user_settings[chat_id] = {
            'digest_interval': 2,  # hours
            'last_digest': None,
            'last_important_check': None,
            'important_senders': set(),
            'notifications_enabled': True
        }
        
        welcome_text = (
            "👋 Welcome to Gmail Digest Assistant!\n\n"
            "I'll help you manage your Gmail inbox by providing:\n"
            "• Regular email digests every 2 hours\n"
            "• Real-time notifications for important emails\n"
            "• Easy email management through commands\n\n"
            "Use the buttons below or these commands:\n"
            "/digest - Get immediate digest\n"
            "/set_interval <hours> - Set digest interval\n"
            "/mark_important <email> - Mark sender as important\n"
            "/settings - View current settings\n"
            "/toggle_notifications - Enable/disable real-time notifications\n"
            "/reauthorize - Force Google reauthorization"
        )
        
        # Create keyboard with buttons
        keyboard = [
            [InlineKeyboardButton("📨 Get Digest", callback_data="get_digest")],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="show_settings"),
                InlineKeyboardButton("📊 Set Interval", callback_data="set_interval")
            ],
            [InlineKeyboardButton("⭐ Mark Important", callback_data="mark_important")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
        # Start periodic digest job
        job_queue = context.job_queue
        job_queue.run_repeating(
            self._send_periodic_digest,
            interval=timedelta(hours=2),
            first=timedelta(minutes=1),
            chat_id=chat_id,
            name=f'digest_{chat_id}'
        )
        
        # Start checking important emails job
        job_queue.run_repeating(
            self._check_important_emails,
            interval=timedelta(minutes=self.check_interval_minutes),
            first=timedelta(minutes=2),
            chat_id=chat_id,
            name=f'important_{chat_id}'
        )
        
        logger.info(f"Started jobs for chat_id {chat_id}")
        
    async def digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /digest command: show one email at a time with navigation buttons."""
        chat_id = update.effective_chat.id
        await update.message.reply_text("Generating digest, please wait...")
        try:
            entries = await self._generate_digest(chat_id)
            if not entries:
                await update.message.reply_text("No new emails since last digest! 📭")
                return
            context.user_data["digest_entries"] = entries
            context.user_data["digest_index"] = 0
            await self._send_digest_entry(update, context, chat_id, 0)
        except Exception as e:
            logger.error(f"Error generating digest: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, there was an error generating your digest. Please try again later."
            )

    async def _send_digest_entry(self, update, context, chat_id, index):
        entries = context.user_data.get("digest_entries", [])
        if not entries or index >= len(entries):
            if getattr(update, "message", None):
                await update.message.reply_text("No more emails in this digest.")
            elif getattr(update, "callback_query", None):
                await update.callback_query.edit_message_text("No more emails in this digest.")
            return
        entry, sender, subject, message_id = entries[index]
        email_id = f"{hash(sender + subject)}"
        keyboard = [
            [
                InlineKeyboardButton("⭐ Mark Important", callback_data=f"markimportant_{email_id}")
            ],
            [
                InlineKeyboardButton("📤 Forward", callback_data=f"forward_{email_id}"),
                InlineKeyboardButton("🚫 Leave Unread", callback_data="leave_unread"),
                InlineKeyboardButton("➡️ Next Email", callback_data="next_email")
            ],
            [
                InlineKeyboardButton("📅 Add to Calendar", callback_data=f"addcal_{email_id}")
            ]
        ]
        if getattr(update, "message", None):
            await update.message.reply_text(
                entry.strip(),
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif getattr(update, "callback_query", None):
            await update.callback_query.edit_message_text(
                entry.strip(),
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def set_interval(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /set_interval command"""
        chat_id = update.effective_chat.id
        
        # If called with arguments, process them
        if context.args:
            try:
                hours = float(context.args[0])
                await self._update_interval(chat_id, hours, context, update=update)
            except (IndexError, ValueError) as e:
                await update.message.reply_text(
                    "⚠️ Please provide a valid interval in hours (0.5-24)\n"
                    "Example: /set_interval 2"
                )
            return
                
        # If called without arguments, show interval selection buttons
        keyboard = [
            [
                InlineKeyboardButton("0.5 hours", callback_data="interval_0.5"),
                InlineKeyboardButton("1 hour", callback_data="interval_1"),
                InlineKeyboardButton("2 hours", callback_data="interval_2"),
            ],
            [
                InlineKeyboardButton("4 hours", callback_data="interval_4"),
                InlineKeyboardButton("8 hours", callback_data="interval_8"),
                InlineKeyboardButton("12 hours", callback_data="interval_12"),
            ],
            [
                InlineKeyboardButton("24 hours", callback_data="interval_24"),
                InlineKeyboardButton("Custom...", callback_data="interval_custom")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Select digest interval:",
            reply_markup=reply_markup
        )
            
    async def _update_interval(self, chat_id: int, hours: float, context: ContextTypes.DEFAULT_TYPE, 
                               update: Optional[Update] = None, callback_query = None) -> None:
        """Update the digest interval"""
        if hours < 0.5 or hours > 24:
            message = "⚠️ Interval must be between 0.5 and 24 hours"
            if callback_query:
                await callback_query.edit_message_text(message)
            elif update:
                await update.message.reply_text(message)
            return
            
        # Update settings
        self.user_settings[chat_id]['digest_interval'] = hours
        
        # Update job interval
        job_queue = context.job_queue
        current_jobs = job_queue.get_jobs_by_name(f'digest_{chat_id}')
        for job in current_jobs:
            job.schedule_removal()
            
        job_queue.run_repeating(
            self._send_periodic_digest,
            interval=timedelta(hours=hours),
            first=timedelta(minutes=1),
            chat_id=chat_id,
            name=f'digest_{chat_id}'
        )
        
        # Send confirmation
        success_message = f"✅ Digest interval updated to {hours} hours"
        if callback_query:
            await callback_query.edit_message_text(
                success_message,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Settings", callback_data="show_settings")
                ]])
            )
        elif update:
            await update.message.reply_text(success_message)
            
    async def mark_important(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /mark_important command"""
        chat_id = update.effective_chat.id
        
        # If called with arguments, process them
        if context.args:
            try:
                email = context.args[0]
                await self._mark_sender_important(email, chat_id, update=update)
            except IndexError:
                await update.message.reply_text(
                    "⚠️ Please provide an email address\n"
                    "Example: /mark_important example@gmail.com"
                )
            return
                
        # If called without arguments, ask for email
        await update.message.reply_text(
            "Please enter the email address to mark as important in the format:\n"
            "/mark_important example@gmail.com"
        )
            
    async def _mark_sender_important(self, email: str, chat_id: int, 
                                    update: Optional[Update] = None, callback_query = None) -> None:
        """Mark a sender as important"""
        success = self.gmail_service.mark_sender_important(email)
        
        if success:
            self.user_settings[chat_id]['important_senders'].add(email)
            success_message = f"✅ Marked {email} as important sender"
            
            if callback_query:
                await callback_query.edit_message_text(
                    success_message,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back to Settings", callback_data="show_settings")
                    ]])
                )
            elif update:
                await update.message.reply_text(success_message)
        else:
            failure_message = "⚠️ Failed to mark sender as important"
            if callback_query:
                await callback_query.edit_message_text(failure_message)
            elif update:
                await update.message.reply_text(failure_message)
            
    async def settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command"""
        chat_id = update.effective_chat.id
        await self._show_settings(chat_id, update=update)
            
    async def _show_settings(self, chat_id: int, update: Optional[Update] = None, 
                            callback_query = None) -> None:
        """Display user settings with interactive buttons"""
        user_config = self.user_settings.get(chat_id, {})
        
        notification_status = '✅ Enabled' if user_config.get('notifications_enabled', True) else '❌ Disabled'
        
        settings_text = (
            "⚙️ Your current settings:\n\n"
            f"📊 Digest Interval: {user_config.get('digest_interval', 2)} hours\n"
            f"⭐ Important Senders: {len(user_config.get('important_senders', set()))}\n"
            f"🔔 Notifications: {notification_status}\n"
            f"📅 Last Digest: {user_config.get('last_digest', 'Never')}"
        )
        
        # Create settings keyboard
        keyboard = [
            [InlineKeyboardButton("📊 Change Interval", callback_data="set_interval")],
            [InlineKeyboardButton("⭐ Mark Important Sender", callback_data="mark_important")],
            [
                InlineKeyboardButton(
                    "🔕 Disable Notifications" if user_config.get('notifications_enabled', True) else "🔔 Enable Notifications", 
                    callback_data="toggle_notifications"
                )
            ],
            [InlineKeyboardButton("📨 Get Digest Now", callback_data="get_digest")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if callback_query:
            await callback_query.edit_message_text(settings_text, reply_markup=reply_markup)
        elif update:
            await update.message.reply_text(settings_text, reply_markup=reply_markup)
        
    async def toggle_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /toggle_notifications command"""
        chat_id = update.effective_chat.id
        await self._toggle_notifications(chat_id, update=update)
            
    async def _toggle_notifications(self, chat_id: int, update: Optional[Update] = None, 
                                   callback_query = None) -> None:
        """Toggle notification setting"""
        if chat_id not in self.user_settings:
            self.user_settings[chat_id] = {'notifications_enabled': True}
            
        # Toggle notification setting
        current = self.user_settings[chat_id].get('notifications_enabled', True)
        self.user_settings[chat_id]['notifications_enabled'] = not current
        
        status = 'enabled' if self.user_settings[chat_id]['notifications_enabled'] else 'disabled'
        message = f"🔔 Real-time notifications are now {status}"
        
        if callback_query:
            # After toggling, show settings again with updated status
            await self._show_settings(chat_id, callback_query=callback_query)
        elif update:
            await update.message.reply_text(message)
            
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        chat_id = query.message.chat_id
        await query.answer()
        data = query.data
        confirmation = None
        advance = False
        mark_read_and_archive = False
        forward_email = False
        add_to_calendar = False
        if data.startswith("markimportant_"):
            email_id = data[len("markimportant_"):]
            confirmation = "✅ Sender marked as important!"
            advance = False  # Do not advance to next email
        elif data.startswith("forward_"):
            email_id = data[len("forward_"):]
            advance = True
            forward_email = True
            mark_read_and_archive = True
        elif data == "next_email":
            advance = True
            mark_read_and_archive = True
            # add_to_calendar = True  # Commented out: no auto calendar integration
        elif data == "leave_unread":
            advance = True
            mark_read_and_archive = False
            # add_to_calendar = False
        elif data.startswith("addcal_"):
            email_id = data[len("addcal_"):]
            # Manually add to calendar when user clicks button
            index = context.user_data.get("digest_index", 0)
            entries = context.user_data.get("digest_entries", [])
            if 0 <= index < len(entries):
                _, sender, subject, message_id = entries[index]
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                start_time = now
                end_time = now + timedelta(hours=1)
                body = ""
                try:
                    msg = self.gmail_service.get_messages(query=f"subject:'{subject}'")
                    if msg and isinstance(msg, list):
                        body = msg[0].get('body', '')
                except Exception:
                    pass
                event_id = self.gmail_service.create_calendar_event(
                    title=subject,
                    start_time=start_time,
                    end_time=end_time,
                    description=body
                )
                if event_id:
                    confirmation = "📅 Calendar event created!"
                else:
                    confirmation = "⚠️ Failed to create calendar event."
                # Stay on the same email after adding to calendar
                entry, sender, subject, _ = entries[index]
                email_id = f"{hash(sender + subject)}"
                keyboard = [
                    [
                        InlineKeyboardButton("⭐ Mark Important", callback_data=f"markimportant_{email_id}"),
                        InlineKeyboardButton("📤 Forward", callback_data=f"forward_{email_id}"),
                        InlineKeyboardButton("🚫 Leave Unread", callback_data="leave_unread"),
                        InlineKeyboardButton("➡️ Next Email", callback_data="next_email"),
                        InlineKeyboardButton("📅 Add to Calendar", callback_data=f"addcal_{email_id}")
                    ]
                ]
                if confirmation:
                    entry = f"{confirmation}\n\n{entry}"
                await query.edit_message_text(
                    entry.strip(),
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
        if advance or data.startswith("markimportant_"):
            index = context.user_data.get("digest_index", 0)
            entries = context.user_data.get("digest_entries", [])
            if 0 <= index < len(entries):
                _, sender, subject, message_id = entries[index]
                if data.startswith("markimportant_"):
                    # Mark sender as important
                    self.gmail_service.mark_sender_important(sender)
                    self.user_settings[chat_id]['important_senders'].add(sender)
                if forward_email:
                    try:
                        result = self.gmail_service.forward_email(
                            message_id,
                            self.forward_address,
                            f"Fwd: {subject}"
                        )
                        if result:
                            confirmation = "📤 Email forwarded!"
                        else:
                            confirmation = "⚠️ Failed to forward email."
                    except Exception as e:
                        logger.error(f"Failed to forward email: {e}")
                        confirmation = "⚠️ Failed to forward email."
                if mark_read_and_archive:
                    try:
                        self.gmail_service.mark_as_read_and_archive(message_id)
                    except Exception as e:
                        logger.error(f"Failed to mark as read/archive: {e}")
            if advance:
                index += 1
                context.user_data["digest_index"] = index
                if index < len(entries):
                    entry, sender, subject, _ = entries[index]
                    email_id = f"{hash(sender + subject)}"
                    keyboard = [
                        [
                            InlineKeyboardButton("⭐ Mark Important", callback_data=f"markimportant_{email_id}")
                        ],
                        [
                            InlineKeyboardButton("📤 Forward", callback_data=f"forward_{email_id}"),
                            InlineKeyboardButton("🚫 Leave Unread", callback_data="leave_unread"),
                            InlineKeyboardButton("➡️ Next Email", callback_data="next_email")
                        ],
                        [
                            InlineKeyboardButton("📅 Add to Calendar", callback_data=f"addcal_{email_id}")
                        ]
                    ]
                    if confirmation:
                        entry = f"{confirmation}\n\n{entry}"
                    await query.edit_message_text(
                        entry.strip(),
                        parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await query.edit_message_text("No more emails in this digest.")
            elif data.startswith("markimportant_"):
                # Stay on the same email, just show confirmation
                entry, sender, subject, _ = entries[index]
                email_id = f"{hash(sender + subject)}"
                keyboard = [
                    [
                        InlineKeyboardButton("⭐ Mark Important", callback_data=f"markimportant_{email_id}")
                    ],
                    [
                        InlineKeyboardButton("📤 Forward", callback_data=f"forward_{email_id}"),
                        InlineKeyboardButton("🚫 Leave Unread", callback_data="leave_unread"),
                        InlineKeyboardButton("➡️ Next Email", callback_data="next_email")
                    ],
                    [
                        InlineKeyboardButton("📅 Add to Calendar", callback_data=f"addcal_{email_id}")
                    ]
                ]
                if confirmation:
                    entry = f"{confirmation}\n\n{entry}"
                await query.edit_message_text(
                    entry.strip(),
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            return
        elif data == "get_digest":
            await query.edit_message_text("Generating digest, please wait...")
            try:
                entries = await self._generate_digest(chat_id)
                if not entries:
                    await query.edit_message_text("No new emails since last digest! 📭")
                    return
                # Store entries and index in user_data for navigation
                context.user_data["digest_entries"] = entries
                context.user_data["digest_index"] = 0
                await self._send_digest_entry(update, context, chat_id, 0)
            except Exception as e:
                logger.error(f"Error generating digest: {e}", exc_info=True)
                await query.edit_message_text("Sorry, there was an error generating your digest. Please try again later.")
                
        elif data == "show_settings":
            await self._show_settings(chat_id, callback_query=query)
            
        elif data == "toggle_notifications":
            await self._toggle_notifications(chat_id, callback_query=query)
            
        elif data == "set_interval":
            # Show interval selection buttons
            keyboard = [
                [
                    InlineKeyboardButton("0.5 hours", callback_data="interval_0.5"),
                    InlineKeyboardButton("1 hour", callback_data="interval_1"),
                    InlineKeyboardButton("2 hours", callback_data="interval_2"),
                ],
                [
                    InlineKeyboardButton("4 hours", callback_data="interval_4"),
                    InlineKeyboardButton("8 hours", callback_data="interval_8"),
                    InlineKeyboardButton("12 hours", callback_data="interval_12"),
                ],
                [
                    InlineKeyboardButton("24 hours", callback_data="interval_24"),
                    InlineKeyboardButton("⬅️ Back", callback_data="show_settings")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Select digest interval:",
                reply_markup=reply_markup
            )
        elif data.startswith("interval_"):
            if data == "interval_custom":
                await query.edit_message_text(
                    "Please use the command /set_interval <hours> to set a custom interval.\n"
                    "Example: /set_interval 3.5",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("⬅️ Back", callback_data="set_interval")
                    ]])
                )
            else:
                # Extract hours from callback data
                hours = float(data.split("_")[1])
                await self._update_interval(chat_id, hours, context, callback_query=query)
                
        elif data == "mark_important":
            await query.edit_message_text(
                "Please enter the email address to mark as important in the format:\n"
                "/mark_important example@gmail.com",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back to Settings", callback_data="show_settings")
                ]])
            )
            
    async def _generate_digest(self, chat_id: int):
        """Generate email digest as a list of (summary, sender, subject, message_id) tuples for each entry."""
        if chat_id not in self.user_settings:
            self.user_settings[chat_id] = {
                'digest_interval': 2,
                'last_digest': None,
                'last_important_check': None,
                'important_senders': set(),
                'notifications_enabled': True
            }
        try:
            # Only load unread emails in inbox
            query = 'is:unread in:inbox'
            messages = self.gmail_service.get_messages(
                max_results=50,
                query=query
            )
            if not messages:
                return []
            sender_groups = {}
            for msg in messages:
                sender = msg['from']
                if sender not in sender_groups:
                    sender_groups[sender] = []
                sender_groups[sender].append(msg)
            entries = []
            anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
            def get_urgency(msgs):
                if any(sender in self.user_settings[chat_id]['important_senders'] for sender in [m['from'] for m in msgs]):
                    return "Important Sender"
                for msg in msgs:
                    urgency_reason = self._get_urgency_reason(msg)
                    if urgency_reason.get('keywords') or urgency_reason.get('deadline'):
                        return f"Urgent: {', '.join(urgency_reason.get('keywords', []))} {urgency_reason.get('deadline', '')}".strip()
                return "Normal"
            for sender, msgs in sender_groups.items():
                if len(msgs) > 1:
                    combined_subjects = "; ".join(sorted(set(m['subject'] for m in msgs)))
                    if len(combined_subjects) > 200:
                        combined_subjects = combined_subjects[:197] + '...'
                    combined_bodies = "\n\n".join(sorted(set(m['body'] for m in msgs)))
                    urgency = get_urgency(msgs)
                    summary, _ = robust_summarize(combined_subjects, combined_bodies, anthropic_api_key, char_limit=1000)
                    summary = clean_summary(html_escape(summary))
                    if len(summary) > 1000:
                        summary = summary[:997] + '...'
                    # Use the first message's id for actions
                    entries.append((f"Sender: {html_escape(sender)}\nSubject: {html_escape(combined_subjects)}\nSuggested Urgency: {urgency_marker(urgency)}\nSummary: {summary}", sender, combined_subjects, msgs[0]['id']))
                else:
                    msg = msgs[0]
                    subject = msg['subject']
                    if len(subject) > 200:
                        subject = subject[:197] + '...'
                    urgency = get_urgency([msg])
                    summary, _ = robust_summarize(subject, msg['body'], anthropic_api_key, char_limit=500)
                    summary = clean_summary(html_escape(summary))
                    if len(summary) > 500:
                        summary = summary[:497] + '...'
                    entries.append((f"Sender: {html_escape(msg['from'])}\nSubject: {html_escape(subject)}\nSuggested Urgency: {urgency_marker(urgency)}\nSummary: {summary}", msg['from'], subject, msg['id']))
            self.user_settings[chat_id]['last_digest'] = datetime.now()
            return entries
        except Exception as e:
            logger.error(f"Error generating digest: {e}", exc_info=True)
            raise
            
    def _is_urgent(self, message: Dict) -> bool:
        """Check if a message is urgent based on content"""
        # Check for urgent keywords in subject
        urgent_keywords = {'urgent', 'asap', 'emergency', 'important', 'action required', 'deadline'}
        subject_lower = message['subject'].lower()
        
        if any(keyword in subject_lower for keyword in urgent_keywords):
            return True
            
        # Check for deadlines in the next 72 hours
        body_lower = message.get('body', '').lower()
        
        # Look for dates in various formats
        date_patterns = [
            r'due by[:\s]*(.*?)(?=\.|$|\n)',
            r'deadline[:\s]*(.*?)(?=\.|$|\n)',
            r'due date[:\s]*(.*?)(?=\.|$|\n)',
            r'submit by[:\s]*(.*?)(?=\.|$|\n)',
            r'complete by[:\s]*(.*?)(?=\.|$|\n)'
        ]
        
        now = datetime.now()
        for pattern in date_patterns:
            matches = re.findall(pattern, body_lower)
            for match in matches:
                parsed_date = self._parse_date(match.strip())
                if parsed_date:
                    time_diff = parsed_date - now
                    if time_diff.total_seconds() > 0 and time_diff.total_seconds() < 72 * 3600:
                        return True
        
        return False
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse a date string into a datetime object"""
        try:
            # Try to parse the date string using dateparser
            parsed_date = dateparser.parse(date_str, settings={'PREFER_DATES_FROM': 'future'})
            return parsed_date
        except Exception:
            return None
            
    def _get_urgency_reason(self, message: Dict) -> Dict[str, Any]:
        """Get the reason why a message is urgent"""
        result = {}
        
        # Check for urgent keywords in subject
        urgent_keywords = {'urgent', 'asap', 'emergency', 'important', 'action required', 'deadline'}
        subject_lower = message['subject'].lower()
        
        found_keywords = [kw for kw in urgent_keywords if kw in subject_lower]
        if found_keywords:
            result['keywords'] = found_keywords
            
        # Check for deadlines
        body_lower = message.get('body', '').lower()
        
        # Look for dates in various formats
        date_patterns = [
            r'due by[:\s]*(.*?)(?=\.|$|\n)',
            r'deadline[:\s]*(.*?)(?=\.|$|\n)',
            r'due date[:\s]*(.*?)(?=\.|$|\n)',
            r'submit by[:\s]*(.*?)(?=\.|$|\n)',
            r'complete by[:\s]*(.*?)(?=\.|$|\n)'
        ]
        
        now = datetime.now()
        closest_deadline = None
        deadline_text = None
        
        for pattern in date_patterns:
            matches = re.findall(pattern, body_lower)
            for match in matches:
                parsed_date = self._parse_date(match.strip())
                if parsed_date:
                    time_diff = parsed_date - now
                    if time_diff.total_seconds() > 0:
                        if not closest_deadline or parsed_date < closest_deadline:
                            closest_deadline = parsed_date
                            deadline_text = f"{parsed_date.strftime('%Y-%m-%d %H:%M')} ({match.strip()})"
        
        if closest_deadline:
            result['deadline'] = deadline_text
            
        return result
            
    async def _check_important_emails(self, context: CallbackContext) -> None:
        """Check for new important emails"""
        chat_id = context.job.chat_id
        user_settings = self.user_settings.get(chat_id, {})
        
        # Skip if notifications are disabled
        if not user_settings.get('notifications_enabled', True):
            return
            
        try:
            # Get last check time
            last_check = user_settings.get('last_important_check')
            query = 'is:unread'
            if last_check:
                query += f' after:{last_check.strftime("%Y/%m/%d")}'
                
            # Get new messages
            messages = self.gmail_service.get_messages(
                max_results=15,
                query=query
            )
            
            # Filter to urgent/important ones
            important_messages = [
                msg for msg in messages 
                if msg['from'] in user_settings.get('important_senders', set()) or self._is_urgent(msg)
            ]
            
            # Send notifications for important messages
            for msg in important_messages:
                reason = ""
                urgency_info = self._get_urgency_reason(msg)
                
                if msg['from'] in user_settings.get('important_senders', set()):
                    reason = "Important sender"
                elif urgency_info.get('keywords'):
                    reason = f"Detected urgency: {', '.join(urgency_info.get('keywords', []))}"
                elif urgency_info.get('deadline'):
                    reason = f"Deadline detected: {urgency_info.get('deadline')}"
                
                notification = (
                    f"🚨 Important Email Alert!\n\n"
                    f"From: {msg['from']}\n"
                    f"Subject: {msg['subject']}\n"
                    f"Received: {msg['date'].strftime('%Y-%m-%d %H:%M')}\n"
                    f"Reason: {reason}"
                )
                
                # Add buttons for quick actions
                keyboard = [
                    [InlineKeyboardButton("📨 View in Gmail", url=f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}")],
                    [
                        InlineKeyboardButton("📤 Forward", callback_data=f"forward_{msg['id']}"),
                        InlineKeyboardButton("✓ Mark Read", callback_data=f"read_{msg['id']}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=notification,
                    reply_markup=reply_markup
                )
                
                # Forward important emails to personal address
                try:
                    self.gmail_service.forward_email(
                        msg['id'],
                        self.forward_address,
                        f"Fwd: {msg['subject']} [IMPORTANT]"
                    )
                    logger.info(f"Forwarded important email {msg['id']} to {self.forward_address}")
                except Exception as e:
                    logger.error(f"Error forwarding email: {e}")
            
            # Update last check time
            self.user_settings[chat_id]['last_important_check'] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error checking important emails: {e}")
            
    async def _send_periodic_digest(self, context: CallbackContext) -> None:
        """Send periodic digest to user"""
        chat_id = context.job.chat_id
        try:
            entries = await self._generate_digest(chat_id)
            if not entries:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Error generating digest. Please try again later."
                )
                return
            
            # Add buttons for actions
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="get_digest")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="show_settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            for entry, sender, subject, _ in entries:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=entry.strip(),
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error sending periodic digest: {e}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Error generating digest. Please try again later."
            )
            
    async def commands(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /commands command to show main menu buttons"""
        keyboard = [
            [InlineKeyboardButton("📨 Get Digest", callback_data="get_digest")],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="show_settings"),
                InlineKeyboardButton("📊 Set Interval", callback_data="set_interval")
            ],
            [InlineKeyboardButton("⭐ Mark Important", callback_data="mark_important")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Main Menu:", reply_markup=reply_markup)
            
    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command: disables all jobs and notifications for the user."""
        chat_id = update.effective_chat.id
        # Remove all jobs for this user
        jobs = context.job_queue.get_jobs_by_name(f'digest_{chat_id}') + context.job_queue.get_jobs_by_name(f'important_{chat_id}')
        for job in jobs:
            job.schedule_removal()
        # Disable notifications
        if chat_id in self.user_settings:
            self.user_settings[chat_id]['notifications_enabled'] = False
        await update.message.reply_text("🛑 All digests and notifications stopped. Use /restart to re-enable.")

    async def restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /restart command: re-enables jobs and notifications for the user."""
        chat_id = update.effective_chat.id
        # Re-initialize user settings if needed
        if chat_id not in self.user_settings:
            self.user_settings[chat_id] = {
                'digest_interval': 2,
                'last_digest': None,
                'last_important_check': None,
                'important_senders': set(),
                'notifications_enabled': True
            }
        else:
            self.user_settings[chat_id]['notifications_enabled'] = True
        # Restart jobs
        job_queue = context.job_queue
        job_queue.run_repeating(
            self._send_periodic_digest,
            interval=timedelta(hours=self.user_settings[chat_id]['digest_interval']),
            first=timedelta(minutes=1),
            chat_id=chat_id,
            name=f'digest_{chat_id}'
        )
        job_queue.run_repeating(
            self._check_important_emails,
            interval=timedelta(minutes=self.check_interval_minutes),
            first=timedelta(minutes=2),
            chat_id=chat_id,
            name=f'important_{chat_id}'
        )
        await update.message.reply_text("✅ Digests and notifications restarted.")

    async def reauthorize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reauthorize command to force a new OAuth flow."""
        chat_id = update.effective_chat.id
        try:
            await update.message.reply_text(
                "🔄 Starting Google re-authorization flow... "
                "A browser window may open shortly."
            )
            # Run the blocking OAuth flow in an executor to avoid blocking the event loop
            credentials = await context.application.run_in_executor(
                None, self.auth.force_reauthorize
            )
            # Recreate GmailService with fresh credentials
            self.gmail_service = GmailService(credentials)
            await update.message.reply_text("✅ Authorization complete! You can resume using the bot.")
            logger.info("User %s successfully re-authorized Gmail access", chat_id)
        except Exception as e:
            logger.error("Reauthorization failed: %s", e, exc_info=True)
            await update.message.reply_text(
                "⚠️ Reauthorization failed. Please try again later or check logs."
            )

    def run(self):
        """Run the bot"""
        app = Application.builder().token(self.token).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("digest", self.digest))
        app.add_handler(CommandHandler("set_interval", self.set_interval))
        app.add_handler(CommandHandler("mark_important", self.mark_important))
        app.add_handler(CommandHandler("settings", self.settings))
        app.add_handler(CommandHandler("toggle_notifications", self.toggle_notifications))
        app.add_handler(CommandHandler("commands", self.commands))
        app.add_handler(CommandHandler("stop", self.stop))
        app.add_handler(CommandHandler("restart", self.restart))
        app.add_handler(CommandHandler("reauthorize", self.reauthorize))
        
        # Add callback query handler for buttons
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Start the bot
        app.run_polling() 