# Gmail Digest Assistant v2.0 (beta)

An intelligent, **async-first** companion that keeps your Gmail inbox under control with concise digests, urgency-aware alerts, and one-click calendar actions – all delivered through a Telegram bot.  
Version 2.0 is a _ground-up rewrite_ that modernises the stack, hardens security, and makes the codebase truly extensible.

---

## 🚀 What’s New in v2.0
| Area | v1.x | **v2.0** |
|------|------|----------|
| **Architecture** | Mixed sync/async, monolith | Fully **modular** `src/gda/*` packages, async event-bus |
| **OAuth** | Single `token.pickle`, occasional re-auth | Encrypted **SQLite token store** (`token.db`) with auto-refresh & background renewal |
| **Summaries** | Sumy / Anthropic fallback chain | Tiered chain: Anthropic → OpenAI → Sumy → heuristic, plus reading-time & ML urgency |
| **Calendar** | Manual “Add event” button | NLP **EventDetector**, conflict check, reminder presets |
| **Bot UX** | Commands + basic buttons | Rich **Home menu**, pagination, `/reauthorize`, `/menu`, dark-mode aware formatting |
| **Extensibility** | Hard-wired features | **Plugin** system (`gda.plugins`) – drop-in analytics, custom actions |
| **Config** | `.env` + Tk wizard | **Pydantic-Settings** (`.env.json`) + `gda setup` Qt wizard, 12-Factor ready |
| **CI / Build** | Basic GitHub Actions | Poetry build, Docker slim image, pre-commit hooks, 95 % test coverage target |

---

## 📐 High-Level Architecture
```
Telegram ⟷ Bot Gateway (aiohttp)
                    │   event-bus (asyncio)
   Google APIs ⟷ Application Core
                    ├── auth          (OAuth, token DB)
                    ├── gmail         (fetch / parse / label)
                    ├── summary       (LLM chain, reading-time)
                    ├── calendar      (event CRUD, conflicts)
                    ├── bot           (commands, UI)
                    └── plugins       (opt-in extensions)
```
Everything is non-blocking; background jobs (token refresh, digest cron) run in the same event loop.

---

## 🛠 Installation

### 1. Clone & enter repo
```
git clone https://github.com/yourname/gmaildigest.git
cd gmaildigest
git checkout v2-rebuild
```

### 2. Use Poetry (recommended)
```
curl -sSL https://install.python-poetry.org | python3 -
poetry install --with gui    # add --with gui for the Qt setup wizard
```

### 3. Run the setup wizard
```
poetry run gda setup
```
The wizard creates `.env.json`, encrypts it (optional), and downloads `credentials.json` from your Google Cloud project.

### 4. Start the bot
```
poetry run gda run
```
First launch opens a browser for OAuth.  
Subsequent launches are headless – tokens auto-refresh in the background.

---

## 🐳 Docker Quick-start
```
docker build -t gmaildigest:2.0 .
docker run -it --rm \
  -v $PWD/.env.json:/app/.env.json \
  -v $PWD/credentials.json:/app/credentials.json \
  gmaildigest:2.0
```
Add `-v $PWD/token.db:/app/token.db` if you want refresh-token persistence across container restarts.

---

## 💬 Using the Bot

| Command | Description |
|---------|-------------|
| `/start` | Initialise chat & start scheduled digests |
| `/digest` | Instant unread-email digest |
| `/menu` / `/help` | Show main menu & buttons |
| `/settings` | Adjust interval, notifications, plugins |
| `/reauthorize` | Force new Google OAuth flow |
| `/version` | Display component versions |

Inline buttons allow: ⭐ mark sender important, 📤 forward, 🚫 skip, ➡️ next, 📅 add/ignore event.

---

## 🔐 Security Highlights
* Tokens stored in SQLCipher DB (AES-256) – key supplied via `GDA_AUTH__TOKEN_ENCRYPTION_KEY`.
* Least-privilege OAuth scopes; refresh tokens auto-revoked on `/reauthorize`.
* `.env.json`, `credentials.json`, `token.db` **git-ignored** by default.
* Secrets never echoed to logs; optional Sentry integration for anonymised errors.

---

## ⚙️ Configuration Cheat-Sheet (`.env.json`)
```json
{
  "telegram": {
    "bot_token": "123456:ABC...",
    "default_digest_interval_hours": 2
  },
  "auth": {
    "credentials_path": "credentials.json",
    "token_db_path": "data/token.db",
    "token_encryption_key": "env:GDA_TOKEN_KEY"
  },
  "summary": {
    "anthropic_api_key": "env:CLAUDE_KEY",
    "openai_api_key": "env:OPENAI_KEY",
    "max_summary_length": 400
  },
  "gmail": {
    "forward_email": "me@example.com"
  }
}
```
Values prefixed with `env:` are pulled from environment variables at runtime.

---

## 🧑‍💻 Developer Guide
1. `poetry shell` & `pre-commit install`
2. Run unit tests: `pytest -q`
3. Type-check: `mypy src/`
4. Lint & format: `black . && isort .`

CI runs on Python 3.10-3.12, Ubuntu/macOS/Windows.

---

## 📅 Roadmap
* Slack & Microsoft Teams adapters  
* Voice (TTS) digest playback  
* Auto-suggest “smart replies” and canned responses  
* Edge deploy via WASI + Fermyon Spin (research)

---

## 🙋 FAQ

**Q:** _Will v2 break my v1 data?_  
**A:** v2 uses new storage files; v1’s `token.pickle` is untouched. Keep both branches side-by-side.

**Q:** _Why do I still see “reauthorise” prompts?_  
**A:** Check that `token.db` volume is mounted/persistent and the refresh token hasn’t been revoked by Google.

**Q:** _Can I disable Anthropic/OpenAI usage?_  
**A:** Leave the API keys empty – the app falls back to local Sumy summarisation automatically.

---

© 2025 Kai Peace – MIT License
