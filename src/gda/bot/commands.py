"""
Command registry for Telegram bot.

This module defines a CommandRegistry class to manage and register bot commands,
track available commands, and provide descriptive information for them.
"""
from typing import Callable, Dict, Any, List, Optional

class CommandRegistry:
    """
    Manages and registers bot commands.

    This class provides a centralized way to register command handlers with
    associated metadata, track available commands, and provide descriptive
    information for commands.
    """

    def __init__(self):
        """Initialize the CommandRegistry."""
        self._commands: Dict[str, Dict[str, Any]] = {}

    def register_command(
        self,
        name: str,
        description: str,
        handler: Optional[Callable] = None,
        **kwargs: Any
    ) -> None:
        """
        Register a new command with its metadata.

        Args:
            name: The name of the command (e.g., "start", "digest").
            description: A brief description of what the command does.
            handler: The callable function that handles the command.
            **kwargs: Additional metadata for the command.
        """
        if name in self._commands:
            raise ValueError(f"Command '{name}' is already registered.")

        self._commands[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            **kwargs,
        }

    def get_command_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific command.

        Args:
            name: The name of the command.

        Returns:
            A dictionary containing the command's metadata, or None if not found.
        """
        return self._commands.get(name)

    def get_all_commands(self) -> List[Dict[str, Any]]:
        """
        Get a list of all registered commands with their metadata.

        Returns:
            A list of dictionaries, each representing a registered command.
        """
        return list(self._commands.values())

    def get_command_handler(self, name: str) -> Optional[Callable]:
        """
        Get the handler function for a specific command.

        Args:
            name: The name of the command.

        Returns:
            The callable handler function, or None if not found.
        """
        command_info = self.get_command_info(name)
        return command_info.get("handler") if command_info else None

    def get_help_message(self) -> str:
        """
        Generate a formatted help message for all registered commands.

        Returns:
            A string containing the help message.
        """
        help_lines = ["📚 *Available Commands*\n"]
        for cmd in self._commands.values():
            help_lines.append(f"/{cmd['name']} - {cmd['description']}")
        return "\n".join(help_lines)
