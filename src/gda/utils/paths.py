"""
Path utility module for Gmail Digest Assistant v2.

This module provides functions to resolve paths relative to the package or
execution directory, making the application location-independent.
"""
import os
from pathlib import Path
from typing import Optional, Union


def get_package_root() -> Path:
    """
    Returns the absolute path to the root directory of the 'gda' package.

    This is typically the directory containing the top-level 'gda' __init__.py.
    """
    return Path(__file__).parent.parent.resolve()


def get_project_root() -> Path:
    """
    Returns the absolute path to the project's root directory.

    This function attempts to find the project root by looking for a
    'pyproject.toml' file or a '.git' directory in the current working
    directory or its parents.
    """
    current_path = Path.cwd()
    for parent in [current_path] + list(current_path.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").is_dir():
            return parent.resolve()
    # Fallback to current working directory if no project root is found
    return current_path.resolve()


def resolve_path(
    path: Union[str, Path], base_path: Optional[Path] = None
) -> Path:
    """
    Resolves a given path relative to a base path.

    If the path is absolute, it is returned as is.
    If the path is relative:
    - If `base_path` is provided, it's resolved relative to `base_path`.
    - If `base_path` is None, it's resolved relative to the project root.

    Args:
        path: The path to resolve (can be a string or Path object).
        base_path: Optional base path to resolve against. If None,
                   `get_project_root()` is used.

    Returns:
        An absolute Path object.
    """
    p = Path(path)
    if p.is_absolute():
        return p.resolve()

    if base_path is None:
        base_path = get_project_root()

    return (base_path / p).resolve()


def get_data_dir() -> Path:
    """
    Returns the absolute path to the application's data directory.

    This directory is typically used for storing persistent data like
    token databases, logs, etc. It's resolved relative to the project root.
    """
    return resolve_path("data")


def get_config_dir() -> Path:
    """
    Returns the absolute path to the application's configuration directory.

    This directory is typically used for storing configuration files like
    credentials.json and .env.json. It's resolved relative to the project root.
    """
    return resolve_path("config")


def get_log_dir() -> Path:
    """
    Returns the absolute path to the application's log directory.

    This directory is used for storing application logs. It's resolved
    relative to the project root.
    """
    return resolve_path("logs")


# Example usage (for testing/demonstration purposes)
if __name__ == "__main__":
    print(f"Package Root: {get_package_root()}")
    print(f"Project Root: {get_project_root()}")
    print(f"Resolved 'config/.env.json': {resolve_path('config/.env.json')}")
    print(f"Resolved 'data/token.db': {resolve_path('data/token.db')}")
    print(f"Data Directory: {get_data_dir()}")
    print(f"Config Directory: {get_config_dir()}")
    print(f"Log Directory: {get_log_dir()}")

    # Example of resolving a path relative to package root
    package_file = resolve_path("bot/app.py", base_path=get_package_root())
    print(f"Resolved 'bot/app.py' relative to package root: {package_file}")
