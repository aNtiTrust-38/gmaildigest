# Gmail Digest Assistant v2.0 (Beta)

Gmail Digest Assistant (**GDA**) is an intelligent, _async-first_ personal assistant that keeps your Gmail inbox under control.  
Every few hours it fetches new mail, produces concise AI-powered summaries, highlights urgent items, and delivers everything to you through a friendly Telegram bot — complete with one-tap actions like **Mark Important**, **Forward**, and **Add to Calendar**.

> **Why v2.0?**  
> Version 1 proved the idea but grew into a monolith and occasionally lost its OAuth session.  
> v2 is a **ground-up rewrite** that fixes persistence, security, and extensibility while remaining simple to self-host (macOS/Docker).

---

## ✨ Key Capabilities
* **Persistent OAuth 2.0** – encrypted SQLite token store with auto-refresh; no surprise re-auth.
* **Tiered Summaries** – Anthropic Claude → OpenAI GPT-4 → local Sumy → heuristic fallback.
* **Urgency Scoring** – ML model plus rule-based deadline detection.
* **Calendar Integration** – NLP event detection and conflict checking before you click _Add_.
* **Telegram UX** – Home menu, pagination, `/reauthorize` and dark-mode aware formatting.
* **Modular Core** – clean `src/gda/` packages (`auth`, `gmail`, `summary`, `calendar`, `bot`, `plugins`) with fully-typed async APIs.
* **Path-independent design** – run the assistant from *any* directory where you clone it; no hard-coded paths.

---

## 🖼 High-Level Architecture

```
Telegram  ⇆ Bot Gateway (aiohttp)  ⇆  Event-Bus (asyncio)
                                        │
Google APIs ⇆ Auth  ⇆ GmailSvc  ⇆ Summary ⇆ Calendar
                                        │
                                   Plugins (opt-in)
```

Everything runs in a single asyncio loop: background jobs (token refresh, digest cron) coexist with Telegram polling, so deployment is as easy as `python -m gda.cli run` or `docker compose up`.

---

## 📦 Module Overview

| Package            | Responsibility                                       |
|--------------------|-------------------------------------------------------|
| `gda.auth`         | OAuth flow, encrypted token DB, background refresh    |
| `gda.gmail`        | Gmail API queries, MIME parsing, label operations     |
| `gda.summary`      | Multi-LLM summarisation chain, reading-time estimate  |
| `gda.calendar`     | Google Calendar CRUD, NLP event detector, conflicts   |
| `gda.bot`          | Telegram adapter, command router, rich UI components  |
| `gda.plugins`      | Drop-in extensions (analytics, custom actions)        |
| `gda.config`       | Pydantic-powered settings loader (`.env.json`)        |

The codebase is 100 % type-annotated, test-driven (pytest/pytest-asyncio), and formatted with Black & isort.

---

## 🖥 macOS Quick-Start

These steps have been tested on **macOS 14 (Sonoma)** with Apple-silicon and Intel Macs.

### 0. Prerequisites
```bash
brew install git python@3.11 poetry                        # core tooling
brew install openssl libffi sqlite pysqlcipher             # crypto + SQLCipher
# GUI setup-wizard (optional – skip if you only use CLI/Docker)
brew install qt6                                           
# Docker (optional for container deployment)
brew install --cask docker
# Python runtime (if not using system Python – GDA is tested on **3.10 → 3.11**)
# Using pyenv:
#   brew install pyenv && pyenv install 3.11.9
```

### 1. Clone the repo & switch to v2
```bash
git clone https://github.com/aNtiTrust-38/gmaildigest.git
cd gmaildigest
git checkout v2-rebuild
```

### 2. Install Python dependencies
```bash
# creates an isolated virtual-env under ~/.cache/pypoetry
poetry install -E gui            # add `--without gui` on headless servers
```

### 3. Initial configuration
```bash
# Launch the Qt/Tk wizard – choose your Google credentials.json,
# Telegram bot token, forwarding email, digest interval, etc.
poetry run gda setup
```
This creates `.env.json` (and `credentials.json`/`token.db`) in the project root.  
You may encrypt the config; the wizard handles decrypting on launch.

### 4. Run the bot
```bash
poetry run gda run
```
The first start opens a browser for Google consent. From then on the token
is cached in `data/token.db` and auto-refreshed.

---

## 🐳 macOS Docker / docker-compose

1. **Build the image locally** (or pull one you pushed to GHCR):
```bash
docker compose build          # or: docker build -t gmaildigest:2.0 .
```

2. **Configuration files**  
Create a `config/` folder and copy in:
```
config/
 ├─ .env.json
 └─ credentials.json
```

3. **Launch**  
```bash
export GDA_TOKEN_KEY="mysqlcipherpassword"
docker compose up -d         # runs in background
```
Containers will restart automatically after reboot.  
Logs: `docker compose logs -f gmaildigest`

> **Tip:** Mount `./data/token.db` as shown in `docker-compose.yml` to persist
> refresh tokens across container updates.

---

## 🛠 Advanced Configuration

### Environment-Variable Overrides
`gda.config` reads **.env.json** first, then allows every field to be overridden by an environment variable using the pattern  
`GDA_<SECTION>__<FIELD>` (double underscore between nesting levels).  
Examples:

```bash
# run in one-off container
docker run -e GDA_TELEGRAM__BOT_TOKEN=123:ABC \
           -e GDA_APP__LOG_LEVEL=DEBUG          \
           gmaildigest:2.0
```
* `GDA_TOKEN_KEY` is used if `auth.token_encryption_key` is set to `env:GDA_TOKEN_KEY` in the JSON.
* **Email validation:** GDA relies on Pydantic’s `EmailStr` which at runtime
  needs the `email-validator` package – it is installed automatically via
  Poetry, but if you use another installer be sure to `pip install email-validator`.

### Google Cloud / API Setup
1. Create a project at <https://console.cloud.google.com>.  
2. **Enable APIs:** _Gmail API_ and _Google Calendar API_.  
3. **OAuth Consent Screen:** set type _External_, add scopes:  
   `…/auth/gmail.readonly`, `…/auth/gmail.modify`, `…/auth/gmail.labels`, `…/auth/calendar.events`.  
4. **Credentials → OAuth client ID → Desktop App**, download `credentials.json` and place it beside `.env.json`.

### Telegram Bot Setup (BotFather 90-sec Guide)
```text
/start        (if first time)
/newbot       →  Give it a name
               →  Give it a username ending with ‘bot’
BotFather ➜ token: 123456:ABC-DEF…
```
Copy that token into the setup wizard (or set `GDA_TELEGRAM__BOT_TOKEN`).  
For private use you’re done. In groups/channels:
1. Add the bot to the chat.  
2. Send `/start` once so it learns the chat-id.  
3. (Optional) Disable “Group Privacy” in BotFather → _Bot Settings_.  

---

## 🛡 Troubleshooting & FAQ

| Symptom | Fix |
|---------|-----|
| **Stuck on re-auth every few days** | Ensure `data/token.db` is *persistent* (volume on Docker); check Google Cloud “OAuth tokens” for revocation |
| **`Message_too_long` telegram error** | Big digests are auto-split, but if you changed the code ensure length ≤ 4096 chars |
| **`Can't parse entities` HTML error** | All dynamic content must be HTML-escaped; use `telegram.helpers.escape_html()` |
| **Anthropic 429 / 529** | GDA falls back to Sumy; check `summary.used_fallback` flag in logs |
| **GUI doesn’t open on macOS** | `brew install qt6` or run headless: `poetry run gda setup --cli` (coming soon) |
| **Dependency-solver / email-validator errors** | Ensure you’re on Python 3.10-3.11 and that the package *email-validator* is installed. With Poetry this is automatic; with pip run `pip install email-validator`. |

### FAQ
**Q  Can I run multiple Gmail accounts?**  
A  Planned for 2.1 – token store is multi-account ready, UI work pending.  
  
**Q  Do I need Anthropic/OpenAI keys?**  
A  No. Leave them blank and local summarisation (Sumy) is used.  
  
**Q  How do I rotate the SQLCipher key?**  
A  `poetry run gda auth --reauthorize` will export, re-encrypt, and import automatically.  

## 🗺 Roadmap Snapshot
1. **Core v2 Beta** – persistent OAuth, digest pipeline, Telegram UX (🎯 _you are here_).
2. **Calendar Automation** – auto-suggest reschedules, time-zone handling.
3. **Multi-Workspace** – Slack & Teams adapters.
4. **Voice Digests** – TTS playback for mobile commuters.

> _Contributions & ideas welcome — see `CONTRIBUTING.md` (coming soon)._

---
