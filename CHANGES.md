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