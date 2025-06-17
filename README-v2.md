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
| **Email Forwarding** | Plain-text only | Preserves **HTML formatting & attachments** when forwarding |
| **Path Independence** | Hard-wired paths | Runs from **any cloned directory** – no hard-coded paths |
| **Extensibility** | Hard-wired features | **Plugin** system (`gda.plugins`) – drop-in analytics, custom actions |
| **Dependency Resolution** | Frequent httpx / PTB issues | Pinned compatible ranges, **email-validator** included for Pydantic |

---

## 📐 High-Level Architecture
```
┌─ Telegram ─┐ ⇆ Bot Gateway (aiohttp) ⇆ event-bus (asyncio)
                                    │
                     ┌───────── Application Core ─────────┐
Google APIs ⇆ Auth ⇆ GmailSvc ⇆ Summary ⇆ Calendar ⇆ Plugins
```

Everything is asynchronous; background jobs (token refresh, digest cron) run in the same event loop.

---

## 🛠 Installation

<details>
<summary>macOS Quick-Start</summary>

1. **Prereqs**

```bash
brew install git python@3.11 poetry
brew install openssl libffi sqlite            # crypto libs
brew install qt6                               # GUI wizard (optional)
brew install --cask docker                     # container runtime
```

2. **Clone**

```bash
git clone https://github.com/aNtiTrust-38/gmaildigest.git
cd gmaildigest && git checkout v2-rebuild
```

3. **Install**

```bash
poetry install -E gui              # add --without gui on headless servers
```

4. **Configure**

```bash
poetry run gda setup
```

5. **Run**

```bash
poetry run gda run
```
</details>

---

## 🐳 Docker Compose

```bash
docker compose build
export GDA_TOKEN_KEY="supersecret"
docker compose up -d
```

Mount `./data/token.db` to persist refresh tokens.

---

## 📦 Configuration Cheat-Sheet (`.env.json`)

```json
{
  "telegram": {
    "bot_token": "123:ABC...",
    "default_digest_interval_hours": 2
  },
  "auth": {
    "credentials_path": "credentials.json",
    "token_db_path": "data/token.db",
    "token_encryption_key": "env:GDA_TOKEN_KEY"
  },
  "gmail": {
    "forward_email": "me@example.com"
  },
  "summary": {
    "anthropic_api_key": "env:CLAUDE_KEY",
    "openai_api_key": "env:OPENAI_KEY"
  }
}
```
> GDA uses Pydantic’s `EmailStr`; **email-validator** is therefore required.  
> Poetry installs it automatically – if using `pip`, run `pip install email-validator`.

---

## ⚙️ Advanced Configuration & Dependency Notes

* All settings can be overridden with env-vars: `GDA_<SECTION>__<FIELD>`.
* Dependency conflicts fixed by pinning:
  * `python-telegram-bot` 20.4 ↔ `httpx` < 0.25
  * `anthropic` < 0.25
* If you vendor dependencies manually ensure **email-validator** is present for runtime email validation.

---

## 💬 Bot Commands

| Command | Action |
|---------|--------|
| `/start` | Initialise & schedule digests |
| `/digest` | Immediate unread digest |
| `/menu` | Show main menu |
| `/settings` | Adjust preferences |
| `/reauthorize` | Force new Google OAuth |
| `/version` | Component versions |

Inline buttons provide ⭐ Important, 📤 Forward (now with HTML/attachments), 🚫 Skip, ➡️ Next, 📅 Add Event.

---

## 🛡 Troubleshooting

* **Re-auth loops** – ensure `token.db` volume persists.
* **HTML parse errors** – all content must be HTML-escaped.
* **email-validator ImportError** – install with `pip install email-validator`.
* **PTB / httpx solver loops** – use pinned versions in `pyproject.toml`.

---

## 📅 Roadmap

1. Calendar auto-reschedule & time-zone helpers  
2. Slack / Teams adapters  
3. Voice (TTS) digests  

MIT © 2025 Kai Peace
