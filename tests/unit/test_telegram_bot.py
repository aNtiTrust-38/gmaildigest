"""
Unit tests for Telegram Bot component
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import asyncio
from datetime import datetime, timedelta
from gmaildigest.telegram_bot import GmailDigestBot
from gmaildigest import summarization
import logging

class TestTelegramBot(unittest.TestCase):
    """Test cases for Telegram Bot functionality"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Mock the environment variables
        self.env_patcher = patch.dict('os.environ', {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'FORWARD_EMAIL': 'forward@example.com',
            'CHECK_INTERVAL_MINUTES': '15'
        })
        self.env_patcher.start()
        
        # Mock the GmailAuthenticator and GmailService
        self.auth_patcher = patch('gmaildigest.telegram_bot.GmailAuthenticator')
        self.service_patcher = patch('gmaildigest.telegram_bot.GmailService')
        
        self.mock_auth = self.auth_patcher.start()
        self.mock_service = self.service_patcher.start()
        
        # Set up mock credentials and service
        self.mock_auth_instance = MagicMock()
        self.mock_service_instance = MagicMock()
        self.mock_credentials = MagicMock()
        
        self.mock_auth.return_value = self.mock_auth_instance
        self.mock_auth_instance.get_credentials.return_value = self.mock_credentials
        self.mock_service.return_value = self.mock_service_instance
        
        # Create the bot instance
        self.bot = GmailDigestBot()
        
    def tearDown(self):
        """Clean up after each test"""
        self.env_patcher.stop()
        self.auth_patcher.stop()
        self.service_patcher.stop()
        
    def test_initialization(self):
        """Test bot initialization"""
        self.assertEqual(self.bot.token, 'test_token')
        self.assertEqual(self.bot.forward_address, 'forward@example.com')
        self.assertEqual(self.bot.check_interval_minutes, 15)
        self.assertIsNotNone(self.bot.gmail_service)
        self.assertEqual(self.bot.gmail_service, self.mock_service_instance)
        
    @pytest.mark.asyncio
    async def test_start_command(self):
        """Test the /start command handler"""
        # Mock objects for Update and Context
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up the message mock
        message_mock = AsyncMock()
        update.message = message_mock
        update.effective_chat.id = 123456
        
        # Set up job queue mock
        job_queue_mock = MagicMock()
        context.job_queue = job_queue_mock
        
        # Call the start command handler
        await self.bot.start(update, context)
        
        # Verify user settings were initialized
        self.assertIn(123456, self.bot.user_settings)
        self.assertEqual(self.bot.user_settings[123456]['digest_interval'], 2)
        
        # Verify welcome message was sent
        message_mock.reply_text.assert_called_once()
        
        # Verify jobs were scheduled
        self.assertEqual(job_queue_mock.run_repeating.call_count, 2)
        
    @pytest.mark.asyncio
    async def test_digest_command(self):
        """Test the /digest command handler"""
        # Mock objects
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up message mock
        message_mock = AsyncMock()
        update.message = message_mock
        update.effective_chat.id = 123456
        
        # Set up user settings
        self.bot.user_settings = {123456: {'digest_interval': 2}}
        
        # Mock the _generate_digest method
        self.bot._generate_digest = AsyncMock()
        self.bot._generate_digest.return_value = "Test Digest Content"
        
        # Call the digest command handler
        await self.bot.digest(update, context)
        
        # Verify digest generation was called
        self.bot._generate_digest.assert_called_once_with(123456)
        
        # Verify the digest was sent
        message_mock.reply_text.assert_called_with(
            "Test Digest Content", 
            parse_mode='HTML',
            reply_markup=unittest.mock.ANY  # Check that some markup was provided
        )
        
    @pytest.mark.asyncio
    async def test_set_interval_command(self):
        """Test the /set_interval command handler"""
        # Mock objects
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up message mock
        message_mock = AsyncMock()
        update.message = message_mock
        update.effective_chat.id = 123456
        
        # Set up arguments for the command
        context.args = ['3']
        
        # Set up user settings
        self.bot.user_settings = {123456: {'digest_interval': 2}}
        
        # Set up job queue mock
        job_queue_mock = MagicMock()
        context.job_queue = job_queue_mock
        
        # Mock job removal and creation
        current_jobs_mock = [MagicMock()]
        job_queue_mock.get_jobs_by_name.return_value = current_jobs_mock
        
        # Call the set_interval command handler
        await self.bot.set_interval(update, context)
        
        # Verify the interval was updated in user settings
        self.assertEqual(self.bot.user_settings[123456]['digest_interval'], 3)
        
        # Verify old jobs were removed
        current_jobs_mock[0].schedule_removal.assert_called_once()
        
        # Verify new job was scheduled
        job_queue_mock.run_repeating.assert_called_once()
        
        # Verify confirmation message was sent
        message_mock.reply_text.assert_called_once_with(
            "✅ Digest interval updated to 3 hours"
        )
        
    @pytest.mark.asyncio
    async def test_mark_important_command(self):
        """Test the /mark_important command handler"""
        # Mock objects
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up message mock
        message_mock = AsyncMock()
        update.message = message_mock
        update.effective_chat.id = 123456
        
        # Set up arguments for the command
        context.args = ['test@example.com']
        
        # Set up user settings
        self.bot.user_settings = {123456: {'important_senders': set()}}
        
        # Mock the gmail service mark_sender_important method
        self.mock_service_instance.mark_sender_important.return_value = True
        
        # Call the mark_important command handler
        await self.bot.mark_important(update, context)
        
        # Verify the gmail service was called
        self.mock_service_instance.mark_sender_important.assert_called_once_with('test@example.com')
        
        # Verify the sender was added to important_senders
        self.assertIn('test@example.com', self.bot.user_settings[123456]['important_senders'])
        
        # Verify confirmation message was sent
        message_mock.reply_text.assert_called_once_with(
            "✅ Marked test@example.com as important sender"
        )
        
    @pytest.mark.asyncio
    async def test_settings_command(self):
        """Test the /settings command handler"""
        # Mock objects
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up message mock
        message_mock = AsyncMock()
        update.message = message_mock
        update.effective_chat.id = 123456
        
        # Set up user settings with sample data
        self.bot.user_settings = {
            123456: {
                'digest_interval': 2,
                'important_senders': {'test@example.com', 'important@example.com'},
                'notifications_enabled': True,
                'last_digest': datetime(2023, 1, 1, 12, 0, 0)
            }
        }
        
        # Call the settings command handler
        await self.bot.settings(update, context)
        
        # Verify settings message was sent with buttons
        message_mock.reply_text.assert_called_once()
        args, kwargs = message_mock.reply_text.call_args
        
        # Check that reply_markup was provided (for buttons)
        self.assertIn('reply_markup', kwargs)
        
    @pytest.mark.asyncio
    async def test_toggle_notifications_command(self):
        """Test the /toggle_notifications command handler"""
        # Mock objects
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up message mock
        message_mock = AsyncMock()
        update.message = message_mock
        update.effective_chat.id = 123456
        
        # Set up user settings
        self.bot.user_settings = {123456: {'notifications_enabled': True}}
        
        # Call the toggle_notifications command handler
        await self.bot.toggle_notifications(update, context)
        
        # Verify the setting was toggled
        self.assertFalse(self.bot.user_settings[123456]['notifications_enabled'])
        
        # Verify confirmation message was sent
        message_mock.reply_text.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_handle_callback_get_digest(self):
        """Test button callback for get_digest"""
        # Mock objects
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up callback query mock
        query_mock = AsyncMock()
        update.callback_query = query_mock
        query_mock.data = "get_digest"
        query_mock.message.chat_id = 123456
        
        # Set up user settings
        self.bot.user_settings = {123456: {'digest_interval': 2}}
        
        # Mock the _generate_digest method
        self.bot._generate_digest = AsyncMock()
        self.bot._generate_digest.return_value = "Test Digest Content"
        
        # Call the callback handler
        await self.bot.handle_callback(update, context)
        
        # Verify query was answered
        query_mock.answer.assert_called_once()
        
        # Verify edit message was called
        query_mock.edit_message_text.assert_called()
        
        # Verify digest was generated
        self.bot._generate_digest.assert_called_once_with(123456)
        
    @pytest.mark.asyncio
    async def test_handle_callback_show_settings(self):
        """Test button callback for show_settings"""
        # Mock objects
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up callback query mock
        query_mock = AsyncMock()
        update.callback_query = query_mock
        query_mock.data = "show_settings"
        query_mock.message.chat_id = 123456
        
        # Set up user settings
        self.bot.user_settings = {
            123456: {
                'digest_interval': 2,
                'important_senders': set(),
                'notifications_enabled': True
            }
        }
        
        # Mock the _show_settings method
        self.bot._show_settings = AsyncMock()
        
        # Call the callback handler
        await self.bot.handle_callback(update, context)
        
        # Verify query was answered
        query_mock.answer.assert_called_once()
        
        # Verify _show_settings was called
        self.bot._show_settings.assert_called_once_with(
            123456, 
            callback_query=query_mock
        )
        
    @pytest.mark.asyncio
    async def test_handle_callback_interval_selection(self):
        """Test button callback for interval selection"""
        # Mock objects
        update = AsyncMock()
        context = AsyncMock()
        
        # Set up callback query mock
        query_mock = AsyncMock()
        update.callback_query = query_mock
        query_mock.data = "interval_2"
        query_mock.message.chat_id = 123456
        
        # Set up user settings
        self.bot.user_settings = {123456: {'digest_interval': 1}}
        
        # Mock the _update_interval method
        self.bot._update_interval = AsyncMock()
        
        # Call the callback handler
        await self.bot.handle_callback(update, context)
        
        # Verify query was answered
        query_mock.answer.assert_called_once()
        
        # Verify _update_interval was called with correct parameters
        self.bot._update_interval.assert_called_once_with(
            123456, 
            2.0, 
            context, 
            callback_query=query_mock
        )
        
    @pytest.mark.asyncio
    async def test_generate_digest(self):
        """Test digest generation"""
        # Set up user settings
        chat_id = 123456
        self.bot.user_settings = {
            chat_id: {
                'digest_interval': 2,
                'last_digest': datetime(2023, 1, 1, 12, 0, 0),
                'important_senders': {'important@example.com'}
            }
        }
        
        # Mock email data
        mock_emails = [
            {
                'id': 'msg1',
                'from': 'important@example.com',
                'subject': 'Important Subject',
                'date': datetime(2023, 1, 2, 10, 0, 0),
                'body': 'Important message content'
            },
            {
                'id': 'msg2',
                'from': 'regular@example.com',
                'subject': 'Regular Subject',
                'date': datetime(2023, 1, 2, 11, 0, 0),
                'body': 'Regular message content'
            }
        ]
        
        # Mock the get_messages method
        self.mock_service_instance.get_messages.return_value = mock_emails
        
        # Mock the _is_urgent method
        self.bot._is_urgent = MagicMock(return_value=False)
        
        # Mock the _get_urgency_reason method
        self.bot._get_urgency_reason = MagicMock(return_value={})
        
        # Generate the digest
        result = await self.bot._generate_digest(chat_id)
        
        # Verify the result contains expected content
        self.assertIn("Email Digest", result)
        self.assertIn("Important/Urgent", result)
        self.assertIn("Important Subject", result)
        self.assertIn("Other Updates", result)
        self.assertIn("Regular Subject", result)
        
        # Verify last_digest was updated
        self.assertIsNotNone(self.bot.user_settings[chat_id]['last_digest'])
        
    def test_is_urgent(self):
        """Test urgency detection"""
        # Create test messages
        urgent_subject = {
            'id': 'msg1',
            'subject': 'URGENT: Please review',
            'body': 'This is an urgent message'
        }
        
        urgent_deadline = {
            'id': 'msg2',
            'subject': 'Project Update',
            'body': 'Please complete by tomorrow at 5pm'
        }
        
        not_urgent = {
            'id': 'msg3',
            'subject': 'Weekly Newsletter',
            'body': 'Here are this week\'s updates'
        }
        
        # Mock the _parse_date method
        self.bot._parse_date = MagicMock()
        self.bot._parse_date.side_effect = lambda date_str: datetime.now() + timedelta(hours=24) if 'tomorrow' in date_str else None
        
        # Test urgency detection
        self.assertTrue(self.bot._is_urgent(urgent_subject))
        self.assertTrue(self.bot._is_urgent(urgent_deadline))
        self.assertFalse(self.bot._is_urgent(not_urgent))
        
    @pytest.mark.asyncio
    async def test_check_important_emails(self):
        """Test checking for important emails"""
        # Mock objects
        context = AsyncMock()
        
        # Set up job mock
        job_mock = MagicMock()
        context.job = job_mock
        job_mock.chat_id = 123456
        
        # Set up user settings
        self.bot.user_settings = {
            123456: {
                'notifications_enabled': True,
                'last_important_check': datetime(2023, 1, 1, 12, 0, 0),
                'important_senders': {'important@example.com'}
            }
        }
        
        # Mock email data
        mock_emails = [
            {
                'id': 'msg1',
                'from': 'important@example.com',
                'subject': 'Important Subject',
                'date': datetime(2023, 1, 2, 10, 0, 0),
                'body': 'Important message content'
            }
        ]
        
        # Mock the get_messages method
        self.mock_service_instance.get_messages.return_value = mock_emails
        
        # Mock the _get_urgency_reason method
        self.bot._get_urgency_reason = MagicMock(return_value={'keywords': ['important']})
        
        # Call the method
        await self.bot._check_important_emails(context)
        
        # Verify bot.send_message was called
        context.bot.send_message.assert_called_once()
        
        # Verify forward_email was called
        self.mock_service_instance.forward_email.assert_called_once()
        
        # Verify last_important_check was updated
        self.assertIsNotNone(self.bot.user_settings[123456]['last_important_check'])
        
    @pytest.mark.asyncio
    async def test_generate_digest_with_summarization(self):
        """Test digest generation with summarization and reading time"""
        # Patch summarize_email and estimate_reading_time
        with patch('gmaildigest.telegram_bot.summarize_email') as mock_summarize, \
             patch('gmaildigest.telegram_bot.estimate_reading_time') as mock_reading_time:
            mock_summarize.return_value = "This is a concise summary."
            mock_reading_time.return_value = 2.5
            chat_id = 123456
            self.bot.user_settings = {
                chat_id: {
                    'digest_interval': 2,
                    'last_digest': datetime(2023, 1, 1, 12, 0, 0),
                    'important_senders': {'important@example.com'}
                }
            }
            mock_emails = [
                {
                    'id': 'msg1',
                    'from': 'important@example.com',
                    'subject': 'Important Subject',
                    'date': datetime(2023, 1, 2, 10, 0, 0),
                    'body': 'Important message content'
                },
                {
                    'id': 'msg2',
                    'from': 'regular@example.com',
                    'subject': 'Regular Subject',
                    'date': datetime(2023, 1, 2, 11, 0, 0),
                    'body': 'Regular message content'
                }
            ]
            self.mock_service_instance.get_messages.return_value = mock_emails
            self.bot._is_urgent = MagicMock(return_value=False)
            self.bot._get_urgency_reason = MagicMock(return_value={})
            result = await self.bot._generate_digest(chat_id)
            assert "This is a concise summary." in result
            assert "⏱️ Est. Reading Time: 2.5 min" in result

def test_summarization_fallback_on_429(monkeypatch):
    """
    Test that summarize_email falls back to local summarizer on 429 error and logs the event.
    """
    class FakeAnthropic:
        def __init__(self, api_key):
            pass
        class messages:
            @staticmethod
            def create(*args, **kwargs):
                raise Exception("429 Too Many Requests")
    monkeypatch.setattr(summarization, "anthropic", MagicMock(Anthropic=FakeAnthropic))
    summary, used_fallback = summarization.summarize_email(
        "Test email body for 429 fallback.", api_key="fake-key", max_retries=1
    )
    assert used_fallback is True
    assert "summary" in summary.lower() or len(summary) > 0

def test_summarization_fallback_on_529(monkeypatch):
    """
    Test that summarize_email falls back to local summarizer on 529 error and logs the event.
    """
    class FakeAnthropic:
        def __init__(self, api_key):
            pass
        class messages:
            @staticmethod
            def create(*args, **kwargs):
                raise Exception("529 Rate Limit")
    monkeypatch.setattr(summarization, "anthropic", MagicMock(Anthropic=FakeAnthropic))
    summary, used_fallback = summarization.summarize_email(
        "Test email body for 529 fallback.", api_key="fake-key", max_retries=1
    )
    assert used_fallback is True
    assert "summary" in summary.lower() or len(summary) > 0

def test_telegram_digest_fallback_status(monkeypatch):
    """
    Test that the Telegram bot digest output reflects fallback status when summarization fails over.
    """
    from gmaildigest.telegram_bot import GmailDigestBot
    bot = GmailDigestBot()
    # Patch summarization to always fallback
    monkeypatch.setattr(summarization, "summarize_email", lambda *a, **kw: ("[Fallback summary] This is a fallback.", True))
    # Patch GmailService to return a fake message
    bot.gmail_service.get_messages = MagicMock(return_value=[{
        'id': '123',
        'from': 'test@example.com',
        'subject': 'Test Subject',
        'body': 'Test Body',
        'date': summarization.datetime.now(),
        'labels': []
    }])
    entries = asyncio.run(bot._generate_digest(12345))
    assert any("Fallback" in e[0] for e in entries)

if __name__ == '__main__':
    unittest.main() 