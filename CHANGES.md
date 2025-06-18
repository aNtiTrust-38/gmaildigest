# Gmail Digest Assistant - Changelog

## [Unreleased]
- Urgency display now uses emojis: 🟢 Normal, 🔴 Urgent, ⭐ Important.
- Digest summary logic improved: Claude-style prompt, no subject/body labels, concise paragraph only.
- Subject is truncated to 200 characters if needed.
- Summaries strip links, images, and non-textual content.
- Digest formatting and inline button features iteratively improved for clarity and usability.
- **Robust summarization failover:** Now uses Anthropic API first, then local summarizer, then heuristic fallback. Digest indicates if a local or fallback summary was used.
- **Persistent OAuth:**  Tokens are now auto-refreshed with retry/back-off logic and
  saved with metadata to reduce unexpected re-authorisations.
- **/reauthorize command:**  New Telegram bot command that lets users force a fresh
  Google OAuth flow from chat if needed (e.g., after credential revocation).
- Path-independent design – the assistant now runs correctly from **any** cloned directory (no hard-coded paths).
- Enhanced email forwarding – HTML bodies and attachments are now preserved when forwarding messages.
- Fixed dependency conflict between **python-telegram-bot** 20.x and **httpx** by pinning compatible versions.
- Fixed dependency conflict between **anthropic** and **httpx** by constraining anthropic < 0.25.0.
- Made **pysqlcipher3** optional via Poetry *encrypted_storage* extra to avoid build failures on systems without SQLCipher headers.
- Fixed Pydantic v2 `BaseSettings` import issue – now imported from **pydantic_settings**.
- Added **email-validator** runtime dependency required for Pydantic’s `EmailStr` validation.
- Added proper configuration validation to prevent using **PLACEHOLDER** bot tokens at runtime.
- Fixed JSON serialization of `Path` objects in the setup wizard (no more “Path is not JSON serialisable” error).
- Fixed `SecretStr` handling in the setup wizard by using direct assignment (compatible with Pydantic v2).
- Updated documentation (README / README-v2) for the refined setup flow and improved first-run user experience.
- Fixed configuration loading issues – settings are now reliably loaded from `config/.env.json`.
- Fixed **“Updater still running”** error in Telegram bot startup – bot now shuts down and restarts cleanly using PTB `application.idle()`.
- Further improved path handling and startup error messages, fully supporting execution from **any** working directory.
- Switched bot lifecycle to PTB **`run_polling()`** for a cleaner single-call startup/shutdown sequence.
- Introduced **`run_async_safely()`** utility to integrate asyncio coroutines with Typer CLI while avoiding “event loop already running” runtime errors.
- Added a full **TDD test-suite** (pytest-asyncio + unittest.mock) covering bot lifecycle, configuration loading, and error handling – all current tests pass.

## Earlier Iterations
- See project commit history for previous changes.

## v0.7 (Beta) - Docker Support & Documentation
- Added Dockerfile and instructions for containerized deployment
- Updated README with Docker usage and configuration guidance
- Clarified .env and credentials.json handling for container use
- Marked as beta for broader testing
- Added troubleshooting for NLTK 'punkt_tab' warning in Docker
- Fixed requirements.txt to include nltk, sumy, httpx
- Docker runtime tested with local summarization 