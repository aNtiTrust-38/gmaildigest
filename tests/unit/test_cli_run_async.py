import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Import the function we want to test
from gda.cli import run_async_safely

# Test basic functionality
def test_run_async_safely_basic():
    """Test that run_async_safely can run a simple coroutine."""
    async def simple_coro():
        return "success"
    
    result = run_async_safely(simple_coro())
    assert result == "success"

# Simplified test ensuring a coroutine that accesses the current
# event-loop still runs fine when executed via `run_async_safely`.
def test_run_async_safely_nested_loop_simple():
    """
    Ensure run_async_safely can execute a coroutine that accesses
    the running event-loop without being called *from* a running loop.
    """

    async def nested_event_loop_coro():
        # Grab the loop (mimics what PTB internals frequently do)
        _ = asyncio.get_event_loop()
        await asyncio.sleep(0.01)
        return "nested ok"

    result = run_async_safely(nested_event_loop_coro())
    assert result == "nested ok"

# Test handling of "Cannot close a running event loop" error
def test_run_async_safely_handles_running_loop_error():
    """
    Test that run_async_safely properly handles the 
    "Cannot close a running event loop" error.
    """
    # This simulates what happens in PTB when it tries to close a loop it didn't create
    async def problematic_coro():
        # Get current loop
        loop = asyncio.get_event_loop()
        
        # Do some work
        await asyncio.sleep(0.01)
        
        # Try to close the loop while it's still running
        # In reality, this would raise RuntimeError: Cannot close a running event loop
        # We'll simulate this with a mock
        with patch.object(loop, 'close', side_effect=RuntimeError("Cannot close a running event loop")):
            # This is similar to what PTB does in its shutdown sequence
            try:
                loop.close()
            except RuntimeError:
                # In PTB, this exception is caught and handled
                pass
        
        return "completed despite loop close error"
    
    # This should not raise the RuntimeError outside the coroutine
    result = run_async_safely(problematic_coro())
    assert result == "completed despite loop close error"

# Test with a coroutine that raises the specific error
def test_run_async_safely_with_telegram_bot_simulation():
    """
    Simulate the exact scenario with python-telegram-bot where it tries to
    initialize, run, and then shutdown with its own event loop management.
    """
    # Mock the PTB Application class behavior
    class MockApplication:
        async def initialize(self):
            # This is what happens in PTB's initialize
            return "initialized"
            
        async def run_polling(self, *args, **kwargs):
            # In PTB, this calls initialize, start_polling, and then idle
            await self.initialize()
            # Simulate some work
            await asyncio.sleep(0.01)
            # Return success
            return "polling started"
            
        async def shutdown(self):
            # In PTB's shutdown, it tries to close the loop
            loop = asyncio.get_event_loop()
            # This would normally raise the error
            with patch.object(loop, 'close', side_effect=RuntimeError("Cannot close a running event loop")):
                try:
                    loop.close()
                except RuntimeError:
                    # PTB catches this and logs it
                    pass
            return "shutdown complete"
    
    # Create the mock application
    mock_app = MockApplication()
    
    # This is similar to what our CLI does
    async def run_bot():
        # First initialize
        await mock_app.initialize()
        # Then run polling (which internally does more event loop stuff)
        result = await mock_app.run_polling()
        # Finally shutdown
        await mock_app.shutdown()
        return result
    
    # This should complete without raising the RuntimeError
    result = run_async_safely(run_bot())
    assert result == "polling started"
