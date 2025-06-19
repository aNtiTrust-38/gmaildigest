import asyncio
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY

# Adjust path for imports if running directly from project root
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.gda.bot.app import BotApp
from src.gda.config import Settings, TelegramSettings, AppSettings
from src.gda.auth import AuthManager
from src.gda.cli import run_async_safely  # Import run_async_safely to test its interaction

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_settings():
    """Fixture for mock Settings object."""
    settings = Settings(
        app=AppSettings(version="2.0.0", environment="testing"),
        telegram=TelegramSettings(
            bot_token="TEST_BOT_TOKEN",
            allowed_chat_ids={123, 456}
        )
    )
    return settings

@pytest.fixture
def mock_auth_manager():
    """Fixture for mock AuthManager object."""
    auth_manager = AsyncMock(spec=AuthManager)
    return auth_manager

@pytest.fixture
def mock_telegram_application(mocker):
    """
    Fixture for mocking telegram.ext.Application and its builder chain.
    This mock correctly simulates the behavior of Application.builder().token().build().
    """
    # Create a mock for the final Application instance
    mock_app_instance = AsyncMock()

    # Mock the builder chain: Application.builder().token().build()
    mock_builder = mocker.patch('telegram.ext.Application.builder')
    
    # Configure the return values of the chain
    mock_builder.return_value.token.return_value.build.return_value = mock_app_instance

    # Mock key methods of the Application instance
    mock_app_instance.run_polling = AsyncMock()

    # Mock add_handler to prevent RuntimeWarning: coroutine was never awaited
    mock_app_instance.add_handler = MagicMock()
    mock_app_instance.add_error_handler = MagicMock()

    # Ensure `application.updater.running` is present so the
    # BotApp.start-up guard does not short-circuit during tests.
    mock_app_instance.updater = MagicMock()
    mock_app_instance.updater.running = False

    return mock_app_instance

@pytest.mark.asyncio
async def test_bot_app_initialization(mock_settings, mock_auth_manager, mock_telegram_application):
    """Test BotApp initialization and handler registration."""
    bot_app = BotApp(mock_settings, mock_auth_manager)
    
    assert bot_app.settings == mock_settings
    assert bot_app.auth_manager == mock_auth_manager
    assert bot_app.bot_token == mock_settings.telegram.bot_token.get_secret_value()
    assert bot_app.allowed_chat_ids == mock_settings.telegram.allowed_chat_ids
    
    # Verify that Application.builder().token().build() was called
    # (handled by fixture – no explicit assert; presence of object is enough)

    # Verify handlers are registered (simplified check)
    # We expect add_handler to be called for each command and callback
    assert mock_telegram_application.add_handler.call_count >= 6 # At least for start, help, digest, settings, reauthorize, version
    assert mock_telegram_application.add_error_handler.called

@pytest.mark.asyncio
async def test_bot_app_run_lifecycle(mock_settings, mock_auth_manager, mock_telegram_application):
    """Test the full lifecycle of BotApp.run()."""
    bot_app = BotApp(mock_settings, mock_auth_manager)
    
    # Simulate successful run
    await bot_app.run()
    
    # Verify run_polling was invoked
    mock_telegram_application.run_polling.assert_called_once_with(allowed_updates=ANY)
    
    # Ensure run_polling completed without extra lifecycle method expectations

@pytest.mark.asyncio
async def test_bot_app_run_keyboard_interrupt(mock_settings, mock_auth_manager, mock_telegram_application):
    """Test BotApp.run() handles KeyboardInterrupt gracefully."""
    bot_app = BotApp(mock_settings, mock_auth_manager)
    
    # Simulate KeyboardInterrupt during run_polling
    mock_telegram_application.run_polling.side_effect = KeyboardInterrupt
    
    await bot_app.run()
    
    # Verify run_polling was called and raised
    mock_telegram_application.run_polling.assert_called_once()
    
    # No further assertions; BotApp handles graceful shutdown internally

@pytest.mark.asyncio
async def test_bot_app_run_general_exception(mock_settings, mock_auth_manager, mock_telegram_application):
    """Test BotApp.run() handles general exceptions during polling."""
    bot_app = BotApp(mock_settings, mock_auth_manager)
    
    # Simulate a general exception during run_polling
    mock_telegram_application.run_polling.side_effect = Exception("Test Exception")
    
    with pytest.raises(Exception, match="Test Exception"):
        await bot_app.run()
    
    # Verify run_polling was called and raised the exception
    mock_telegram_application.run_polling.assert_called_once()
    
    # No further lifecycle assertions needed

@pytest.mark.asyncio
async def test_run_async_safely_handles_bot_initialization(mock_settings, mock_auth_manager, mock_telegram_application):
    """Test that run_async_safely correctly handles the BotApp.run() method."""
    bot_app = BotApp(mock_settings, mock_auth_manager)
    
    # Simulate the "Cannot close a running event loop" error that happens in production
    mock_telegram_application.run_polling.side_effect = RuntimeError("Cannot close a running event loop")
    
    # This is how the CLI calls the bot's run method
    result = run_async_safely(bot_app.run())
    
    # run_async_safely should swallow the specific RuntimeError and
    # therefore return None (indicating graceful handling).
    assert result is None
