#!/usr/bin/env python3
"""
Command-line interface for Gmail Digest Assistant v2.

This module provides a command-line interface using Typer for interacting with
the Gmail Digest Assistant application.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Any, Coroutine

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from gda.config import get_settings, load_settings, Settings
from gda.auth import AuthManager
from gda.bot import BotApp

# Create Typer app
app = typer.Typer(
    name="Gmail Digest Assistant",
    help="Intelligent email summarization and notification system",
    add_completion=False,
)

# Rich console for pretty output
console = Console()

# Configure logger
logger = logging.getLogger(__name__)


def run_async_safely(coro: Coroutine) -> Any:
    """
    Run an async coroutine safely, handling both scenarios:
    1. No event loop running: Use asyncio.run()
    2. Event loop already running: Handle appropriately based on context

    This function is designed to run async code from a synchronous context
    (like a CLI command) or from an already running async context (like pytest-asyncio).
    It addresses common issues with event loop management.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine
    """
    # Set environment variable to suppress some asyncio debug warnings
    os.environ['PYTHONASYNCIONOTDEBUG'] = '1'

    try:
        # First attempt: Try to get the current running loop
        try:
            loop = asyncio.get_running_loop()
            logger.debug("Event loop already running, using existing loop")
            
            # Create a future to store the result
            future = asyncio.Future(loop=loop)
            
            # Define a callback to set the future result when the coroutine completes
            async def run_and_set_result():
                try:
                    result = await coro
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
            
            # Schedule the coroutine to run
            asyncio.create_task(run_and_set_result())
            
            # Wait for the future to complete, but handle "already running" errors
            try:
                return loop.run_until_complete(future)
            except RuntimeError as e:
                if "already running" in str(e):
                    logger.debug("Loop already running error, using alternative approach")
                    # In this case, we're likely in a pytest-asyncio environment
                    # The coroutine is already scheduled to run, so we just need to
                    # wait for it to complete. We can't block here, so we'll return None
                    # and let the event loop handle the coroutine.
                    return None
                raise
                
        except RuntimeError:
            # No running loop found, create a new one with asyncio.run()
            logger.debug("No event loop running, using asyncio.run()")
            return asyncio.run(coro)
    
    except RuntimeError as e:
        # Handle the "Cannot close a running event loop" error
        if "Cannot close a running event loop" in str(e):
            logger.warning("Caught 'Cannot close a running event loop' error. "
                          "This is often expected in certain environments (e.g., tests) "
                          "and the operation likely completed successfully.")
            return None
        else:
            # For other RuntimeErrors, log and re-raise
            logger.error(f"Unexpected RuntimeError in run_async_safely: {e}", exc_info=True)
            raise
    
    except Exception as e:
        # Log and re-raise other exceptions
        logger.error(f"Error in run_async_safely: {e}", exc_info=True)
        raise


@app.command("run")
def run_bot(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (.env.json)",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    log_level: Optional[str] = typer.Option(
        None,
        "--log-level",
        "-l",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    ),
    data_dir: Optional[Path] = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Directory for application data",
        dir_okay=True,
        file_okay=False,
    ),
) -> None:
    """Run the Gmail Digest Assistant bot."""
    try:
        # Load settings
        settings = load_settings(config_file)
        
        # Override settings with command line arguments if provided
        if log_level:
            settings.app.log_level = log_level
        if data_dir:
            settings.app.data_dir = data_dir

        # ------------------------------------------------------------------ #
        # Basic config sanity-checks before touching network or OAuth flows  #
        # ------------------------------------------------------------------ #
        # 1. Telegram bot token must be configured (not the placeholder used
        #    during first-run initialisation).
        token_value = (
            settings.telegram.bot_token.get_secret_value()
            if settings.telegram.bot_token
            else None
        )
        if token_value == "PLACEHOLDER" or not token_value:
            console.print(
                "[bold red]Error:[/bold red] Telegram bot token is not configured.\n"
                "Run the setup wizard first: [bold]gda setup[/bold]",
                style="red",
            )
            raise typer.Exit(code=1)

        # 2. Google OAuth credentials.json must exist before we can create
        #    the AuthManager (otherwise the flow will crash later).
        creds_path = Path(settings.auth.credentials_path).expanduser()
        if not creds_path.exists():
            console.print(
                "[bold red]Error:[/bold red] Google OAuth credentials file not found at "
                f"{creds_path}.\nRun [bold]gda setup[/bold] to configure or place the "
                "file manually then retry.",
                style="red",
            )
            raise typer.Exit(code=1)
        
        # Display startup banner
        console.print(
            Panel.fit(
                f"[bold green]Gmail Digest Assistant v{settings.app.version}[/bold green]\n"
                f"[italic]Environment: {settings.app.environment.value}[/italic]",
                title="Starting",
                border_style="green",
            )
        )
        
        # Initialize auth manager
        auth_manager = AuthManager(settings.auth)
        
        # Initialize and run bot
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Starting bot...[/bold green]"),
            transient=True,
        ) as progress:
            progress.add_task("starting", total=None)
            bot_app = BotApp(settings, auth_manager)
            
            # Use our safe runner instead of asyncio.run()
            run_async_safely(bot_app.run())
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")
        raise typer.Exit(code=1)


@app.command("auth")
def check_auth(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (.env.json)",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    reauthorize: bool = typer.Option(
        False,
        "--reauthorize",
        "-r",
        help="Force reauthorization",
    ),
) -> None:
    """Check authentication status or reauthorize."""
    try:
        # Load settings
        settings = load_settings(config_file)
        
        # Initialize auth manager
        auth_manager = AuthManager(settings.auth)
        
        if reauthorize:
            console.print("[yellow]Starting reauthorization process...[/yellow]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold yellow]Reauthorizing...[/bold yellow]"),
                transient=True,
            ) as progress:
                progress.add_task("reauthorizing", total=None)
                # Use our safe runner instead of asyncio.run()
                run_async_safely(auth_manager.force_reauthorize())
            console.print("[green]✓ Reauthorization successful![/green]")
        else:
            # Check auth status
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Checking authentication status...[/bold blue]"),
                transient=True,
            ) as progress:
                progress.add_task("checking", total=None)
                # Use our safe runner instead of asyncio.run()
                status = run_async_safely(auth_manager.check_auth_status())
            
            # Display status table
            table = Table(title="Authentication Status")
            table.add_column("Account", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Expires", style="yellow")
            table.add_column("Refresh Token", style="magenta")
            
            for account, details in status.items():
                table.add_row(
                    account,
                    "✓ Valid" if details["valid"] else "✗ Invalid",
                    details["expires_at"].isoformat() if details.get("expires_at") else "N/A",
                    "Present" if details.get("has_refresh_token") else "Missing",
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")
        raise typer.Exit(code=1)


@app.command("version")
def show_version() -> None:
    """Show version information."""
    settings = get_settings()
    
    # Display version info
    table = Table(title=f"Gmail Digest Assistant v{settings.app.version}")
    table.add_column("Component", style="cyan")
    table.add_column("Version/Status", style="green")
    
    table.add_row("Python", sys.version.split()[0])
    table.add_row("Environment", settings.app.environment.value)
    table.add_row("Log Level", settings.app.log_level.value)
    table.add_row(
        "Anthropic API",
        "Configured" if settings.summary.anthropic_api_key else "Not configured"
    )
    table.add_row(
        "OpenAI API",
        "Configured" if settings.summary.openai_api_key else "Not configured"
    )
    table.add_row(
        "Telegram Bot",
        "Configured" if settings.telegram.bot_token else "Not configured"
    )
    
    console.print(table)


@app.command("setup")
def setup_wizard() -> None:
    """Launch the setup wizard."""
    try:
        # Import here to avoid circular imports
        from gda.setup_config import run_setup_wizard
        
        console.print(
            Panel.fit(
                "[bold blue]Starting Gmail Digest Assistant Setup Wizard[/bold blue]",
                border_style="blue",
            )
        )
        
        # Run the setup wizard
        run_setup_wizard()
        
    except ImportError:
        console.print(
            "[bold red]Error:[/bold red] Setup wizard requires PyQt6. "
            "Install with: pip install gmaildigest[gui]",
            style="red",
        )
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
