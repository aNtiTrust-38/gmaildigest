"""
Setup configuration wizard for Gmail Digest Assistant v2.

This module provides a setup wizard to guide users through the initial
configuration of the application, including setting up API keys, email
addresses, and other preferences. It supports both GUI and CLI modes.
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple

# Rich for CLI mode
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

# Import config classes
from gda.config import Settings, AuthSettings, GmailSettings, TelegramSettings, SummarySettings
from gda.utils.paths import get_config_dir, get_data_dir
# Secret type for safe assignment
from pydantic import SecretStr

# Configure logger
logger = logging.getLogger(__name__)
console = Console()

# Try to import GUI components
GUI_AVAILABLE = False
try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
        QLineEdit, QPushButton, QFileDialog, QComboBox, QMessageBox,
        QCheckBox, QGroupBox, QFormLayout, QDialog, QDialogButtonBox
    )
    from PyQt6.QtCore import Qt
    GUI_AVAILABLE = True
except ImportError:
    logger.warning("PyQt6 not available. GUI wizard will be disabled.")


def _run_cli_wizard() -> Settings:
    """
    Run a command-line based setup wizard.
    
    Returns:
        Settings object with user configuration
    """
    console.print(
        Panel.fit(
            "[bold blue]Gmail Digest Assistant CLI Setup Wizard[/bold blue]",
            border_style="blue",
        )
    )
    
    # Initialize with default settings, providing a temporary bot_token
    # to satisfy Pydantic validation (it will be replaced by user input).
    settings = Settings(telegram=TelegramSettings(bot_token="PLACEHOLDER"))
    
    # Get Telegram Bot Token
    settings.telegram.bot_token = SecretStr(
        Prompt.ask("[bold cyan]Enter your Telegram Bot Token[/bold cyan] (from BotFather)")
    )
    
    # Get Google credentials path
    credentials_path_str = Prompt.ask(
        "[bold cyan]Enter the path to your Google OAuth credentials.json file[/bold cyan]",
        default=str(Path.home() / "Downloads" / "credentials.json")
    )
    credentials_path = Path(credentials_path_str)
    
    if not credentials_path.exists():
        console.print(
            f"[bold yellow]Warning:[/bold yellow] File {credentials_path} not found. "
            "You will need to provide valid credentials before running the application.",
            style="yellow"
        )
    else:
        # Copy credentials to config directory
        config_dir = get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        dest_path = config_dir / "credentials.json"
        try:
            shutil.copy(credentials_path, dest_path)
            settings.auth.credentials_path = dest_path
            console.print(f"Copied credentials to [green]{dest_path}[/green]")
        except Exception as e:
            console.print(f"[bold red]Error copying credentials:[/bold red] {e}", style="red")
    
    # Get forwarding email
    forward_email = Prompt.ask(
        "[bold cyan]Enter the email address for forwarding important emails[/bold cyan]",
        default=""
    )
    if forward_email:
        settings.gmail.forward_email = forward_email
    
    # Get check interval
    check_interval_options = ["15", "30", "60", "1H", "2H", "4H"]
    check_interval = Prompt.ask(
        "[bold cyan]Select check interval for new emails[/bold cyan]",
        choices=check_interval_options,
        default="15"
    )
    
    # Convert to minutes
    if check_interval.endswith("H"):
        minutes = int(check_interval[:-1]) * 60
    else:
        minutes = int(check_interval)
    
    settings.telegram.check_interval_minutes = minutes
    
    # Get digest interval
    digest_interval_options = ["0.5", "1", "2", "4", "8", "12", "24"]
    digest_interval = Prompt.ask(
        "[bold cyan]Select digest interval (hours)[/bold cyan]",
        choices=digest_interval_options,
        default="2"
    )
    settings.telegram.default_digest_interval_hours = float(digest_interval)
    
    # Optional: Anthropic API Key
    if Confirm.ask("[bold cyan]Do you want to configure Anthropic API for better summarization?[/bold cyan]"):
        api_key = Prompt.ask("[bold cyan]Enter your Anthropic API Key[/bold cyan]", password=True)
        settings.summary.anthropic_api_key = SecretStr(api_key)
    
    # Optional: OpenAI API Key
    if Confirm.ask("[bold cyan]Do you want to configure OpenAI API as a fallback?[/bold cyan]"):
        api_key = Prompt.ask("[bold cyan]Enter your OpenAI API Key[/bold cyan]", password=True)
        settings.summary.openai_api_key = SecretStr(api_key)
    
    # Save settings
    save_settings(settings)
    
    console.print(
        Panel.fit(
            "[bold green]Setup complete![/bold green]\n"
            "You can now run the application with: [bold]poetry run gda run[/bold]",
            border_style="green",
        )
    )
    
    return settings


def _run_gui_wizard() -> Optional[Settings]:
    """
    Run a GUI-based setup wizard using PyQt6.
    
    Returns:
        Settings object with user configuration or None if cancelled
    """
    if not GUI_AVAILABLE:
        logger.error("Cannot run GUI wizard: PyQt6 is not installed")
        return None
    
    # Initialize QApplication
    app = QApplication(sys.argv)
    
    # Create wizard dialog
    wizard = SetupWizard()
    result = wizard.exec()
    
    if result == QDialog.DialogCode.Accepted:
        return wizard.get_settings()
    
    return None


class SetupWizard(QDialog):
    """
    GUI Setup Wizard for Gmail Digest Assistant.
    """
    def __init__(self):
        """Initialize the setup wizard dialog."""
        super().__init__()
        
        # Initialize with default settings, using a temporary bot_token
        # which will be replaced when the user enters the real value.
        self.settings = Settings(telegram=TelegramSettings(bot_token="PLACEHOLDER"))
        
        self.setWindowTitle("Gmail Digest Assistant Setup")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Gmail Digest Assistant Setup Wizard")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title_label)
        
        # Form layout for settings
        form_layout = QFormLayout()
        
        # Telegram Bot Token
        self.bot_token_input = QLineEdit()
        form_layout.addRow("Telegram Bot Token:", self.bot_token_input)
        
        # Google Credentials
        creds_layout = QHBoxLayout()
        self.credentials_path_input = QLineEdit()
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_credentials)
        creds_layout.addWidget(self.credentials_path_input)
        creds_layout.addWidget(browse_button)
        form_layout.addRow("Google Credentials:", creds_layout)
        
        # Forwarding Email
        self.forward_email_input = QLineEdit()
        form_layout.addRow("Forward Email:", self.forward_email_input)
        
        # Check Interval
        self.check_interval_combo = QComboBox()
        self.check_interval_combo.addItems(["15 minutes", "30 minutes", "1 hour", "2 hours", "4 hours"])
        self.check_interval_combo.setCurrentIndex(0)
        form_layout.addRow("Check Interval:", self.check_interval_combo)
        
        # Digest Interval
        self.digest_interval_combo = QComboBox()
        self.digest_interval_combo.addItems(["30 minutes", "1 hour", "2 hours", "4 hours", "8 hours", "12 hours", "24 hours"])
        self.digest_interval_combo.setCurrentIndex(2)  # Default to 2 hours
        form_layout.addRow("Digest Interval:", self.digest_interval_combo)
        
        # API Keys (Optional)
        api_group = QGroupBox("Optional API Keys (for better summarization)")
        api_layout = QFormLayout()
        
        self.anthropic_key_input = QLineEdit()
        self.anthropic_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("Anthropic API Key:", self.anthropic_key_input)
        
        self.openai_key_input = QLineEdit()
        self.openai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("OpenAI API Key:", self.openai_key_input)
        
        api_group.setLayout(api_layout)
        
        # Add form layout to main layout
        form_container = QWidget()
        form_container.setLayout(form_layout)
        layout.addWidget(form_container)
        layout.addWidget(api_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def _browse_credentials(self):
        """Open file dialog to browse for credentials.json"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Google Credentials", str(Path.home()), "JSON Files (*.json)"
        )
        if file_path:
            self.credentials_path_input.setText(file_path)
    
    def accept(self):
        """Validate inputs and save settings"""
        # Validate required fields
        if not self.bot_token_input.text().strip():
            QMessageBox.warning(self, "Missing Information", "Please enter your Telegram Bot Token")
            return
        
        # Save settings
        self._update_settings()
        save_settings(self.settings)
        
        # Show success message
        QMessageBox.information(
            self, "Setup Complete", 
            "Configuration saved successfully.\nYou can now run the application with: poetry run gda run"
        )
        
        super().accept()
    
    def _update_settings(self):
        """Update settings object with form values"""
        # Telegram Bot Token
        self.settings.telegram.bot_token = SecretStr(self.bot_token_input.text().strip())
        
        # Google Credentials
        creds_path = self.credentials_path_input.text().strip()
        if creds_path:
            src_path = Path(creds_path)
            if src_path.exists():
                # Copy credentials to config directory
                config_dir = get_config_dir()
                config_dir.mkdir(parents=True, exist_ok=True)
                dest_path = config_dir / "credentials.json"
                try:
                    shutil.copy(src_path, dest_path)
                    self.settings.auth.credentials_path = dest_path
                except Exception as e:
                    logger.error(f"Error copying credentials: {e}")
        
        # Forwarding Email
        if self.forward_email_input.text().strip():
            self.settings.gmail.forward_email = self.forward_email_input.text().strip()
        
        # Check Interval
        check_interval_text = self.check_interval_combo.currentText()
        if "hour" in check_interval_text:
            hours = int(check_interval_text.split()[0])
            self.settings.telegram.check_interval_minutes = hours * 60
        else:
            minutes = int(check_interval_text.split()[0])
            self.settings.telegram.check_interval_minutes = minutes
        
        # Digest Interval
        digest_interval_text = self.digest_interval_combo.currentText()
        if "hour" in digest_interval_text:
            hours = int(digest_interval_text.split()[0])
            self.settings.telegram.default_digest_interval_hours = float(hours)
        else:
            minutes = int(digest_interval_text.split()[0])
            self.settings.telegram.default_digest_interval_hours = float(minutes) / 60
        
        # API Keys
        if self.anthropic_key_input.text().strip():
            self.settings.summary.anthropic_api_key = SecretStr(self.anthropic_key_input.text().strip())
        
        if self.openai_key_input.text().strip():
            self.settings.summary.openai_api_key = SecretStr(self.openai_key_input.text().strip())
    
    def get_settings(self) -> Settings:
        """Get the configured settings"""
        return self.settings


def save_settings(settings: Settings) -> Path:
    """
    Save settings to the config file.
    
    Args:
        settings: Settings object to save
    
    Returns:
        Path to the saved config file
    """
    # Create config directory if it doesn't exist
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Save settings to .env.json
    config_path = config_dir / ".env.json"
    # Convert to JSON-serialisable structure (Paths & SecretStr → str)
    def _to_jsonable(obj: Any) -> Any:  # small, local helper
        from pydantic import SecretStr
        if isinstance(obj, dict):
            return {k: _to_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_to_jsonable(v) for v in obj]
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, SecretStr):
            return obj.get_secret_value()
        return obj

    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(_to_jsonable(settings.dict(exclude_none=True)), fh, indent=2)
    
    logger.info(f"Settings saved to {config_path}")
    return config_path


def run_setup_wizard(cli_mode: bool = False) -> Optional[Settings]:
    """
    Run the setup wizard in either GUI or CLI mode.
    
    Args:
        cli_mode: Force CLI mode even if GUI is available
    
    Returns:
        Settings object if setup was completed, None if cancelled
    """
    try:
        # Create necessary directories
        get_config_dir().mkdir(parents=True, exist_ok=True)
        get_data_dir().mkdir(parents=True, exist_ok=True)
        
        # Run appropriate wizard
        if GUI_AVAILABLE and not cli_mode:
            return _run_gui_wizard()
        else:
            return _run_cli_wizard()
    except Exception as e:
        logger.error(f"Error running setup wizard: {e}", exc_info=True)
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")
        return None


if __name__ == "__main__":
    """Run the setup wizard directly when the module is executed."""
    run_setup_wizard()
