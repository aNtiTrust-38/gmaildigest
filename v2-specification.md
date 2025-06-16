# Gmail Digest Assistant – Version 2.0 Specification

## 1  Goals & Vision
Version 2.0 (“GDA 2”) modernises the Gmail Digest Assistant with a cleaner architecture, stronger security, richer summaries and first-class calendar integration while staying lightweight enough for self-hosted or Docker deployment.

Key objectives  
• Zero-friction, **persistent OAuth** – no surprise re-auth.  
• Multi-tier **summarisation 2.0** – smarter prompts, reading-time estimation, ML urgency scoring.  
• Action-centric **calendar workflows** – detect, preview and add events with conflict checks.  
• Extensible plugin-style modules, 100 % typed & unit-tested.  
• Clear, chat-first UX with Telegram (and later Slack/Mobile push) parity.

---

## 2  High-Level Architecture
```
┌────────────┐            ┌──────────────┐          ┌───────────────┐
│ Telegram   │ ⇆ Bot API ⇆│ Bot Gateway  │ ⇆ Async │ Application    │
│ Clients    │            │ (aiohttp)    │   bus   │ Core           │
└────────────┘            └──────────────┘          │  ├─Auth        │
                                                     │  ├─GmailSvc   │
┌────────────┐   Gmail/Cal REST  ┌──────────────┐    │  ├─Summariser │
│ Google     │⇆  (google-api-py) │  Google APIs │    │  ├─Calendar   │
│ Workspace  │                   └──────────────┘    │  └─Plugins    │
└────────────┘                                        └───────────────┘
```
Everything is asynchronous; a lightweight event bus decouples IO from business logic.  
Each dashed box is a Python package.

---

## 3  Module Breakdown

| Package | Responsibility | Key Classes / Scripts |
|---------|----------------|-----------------------|
| `gda.auth` | Secure OAuth handling; token storage, refresh, revocation, multi-account. | `AuthManager`, `TokenStore` |
| `gda.gmail` | Gmail queries, MIME parsing, batching, label ops. | `GmailService`, `MessageParser` |
| `gda.summary` | Tiered summarisation: Anthropic ‑> OpenAI ‑> Sumy ‑> heuristic; reading-time estimate. | `Summariser`, `FallbackChain` |
| `gda.calendar` | Event extraction, conflict check, Google Calendar CRUD. | `CalendarService`, `EventDetector` |
| `gda.bot` | Telegram adapter, command router, button UI, rate-limit guard. | `BotApp`, `CommandRegistry` |
| `gda.plugins` | Optional features (analytics, learning). | Base `Plugin`, dynamic loader |
| `gda.cli` | `gda.py` – entrypoint supporting CLI flags & Docker. |  |
| `setup_config` | Qt/Tk wizard → `.env.json` + optional encryption. |  |

All code is **type-annotated**, follows **12-Factor** config via `pydantic` settings.

---

## 4  Key Improvements over v1

### 4.1  Persistent OAuth
• Encrypted `token.db` (SQLite + SQLCipher) stores access/refresh tokens per account.  
• Refresh handled by background task with exponential back-off & alert before expiry.  
• `/reauthorise` still available but rarely needed.

### 4.2  Summarisation 2.0
| Layer | When used | Output length |
|-------|-----------|---------------|
| Anthropic Claude 3.5 | API key present & quota OK | ≤ 400 chars |
| OpenAI GPT-4o | fallback 1 | ≤ 400 chars |
| Local Sumy-LSA | offline | ≤ 400 chars |
| Heuristic | last resort | ≤ 400 chars |

Adds:  
- reading-time badge (words ÷ 225 wpm → rounded 0.5 min).  
- ML urgency classifier (sklearn random-forest, model file hot-reloaded).

### 4.3  Calendar Workflows
• `EventDetector` extracts datetime, duration, location, meet links via NLP.  
• Inline buttons: _Add_, _Ignore_, _Suggest time_.  
• Conflict engine compares against primary calendar, annotates **CONFLICT**.

### 4.4  UX Enhancements
- Single “Home” menu (`/menu`) with digest preview, settings, help.  
- Pagination & rate-limit feedback.  
- Theme-aware (dark/light) markdown snippets.

---

## 5  Data Flow
1. Bot receives `/digest`.  
2. `BotApp` emits `GET_DIGEST` event → `DigestController`.  
3. `GmailService` fetches unread threads, `MessageParser` normalises.  
4. `Summariser` produces summary & metadata.  
5. `CalendarService` analyses for events.  
6. `DigestRenderer` builds HTML, pushes chunks to bot.

---

## 6  Implementation Approach

### Phase 1 (Core refactor)  
- Scaffold repo (`src/` layout, poetry).  
- Implement `AuthManager` with SQLite token store & tests.  
- Port GmailService with async google-api-python-client.  
- MVP bot with `/health` & `/reauthorise`.

### Phase 2 (Summarisation & Digest)  
- Build `Summariser` chain.  
- Implement reading-time, urgency classifier.  
- Digest rendering engine + pagination.

### Phase 3 (Calendar & UX)  
- NLP event detector (dateparser + regex).  
- Calendar CRUD with conflict flag.  
- Bot UI overhaul, settings persistence.

### Phase 4 (Polish & Deployment)  
- Docker-slim image, CI GitHub Actions matrix, Sentry integration.  
- Documentation & migration guide v1 → v2.

---

## 7  Non-Functional Requirements
- 95 % unit-test coverage, mutation-tested.  
- P99 Telegram response ≤ 2 s for 50 email digest.  
- Memory footprint ≤ 200 MB in idle container.  
- Secrets never written unencrypted to disk.  

---

## 8  Lessons Learned from v1
| Challenge | Lesson | v2 Mitigation |
|-----------|--------|---------------|
| Refresh token loss | Central token DB + alerts | `TokenStore` + expiry notice |
| Summaries too long / duplicates | Strict char limit, dedup bodies | `DigestRenderer` truncation |
| HTML parse errors | Must escape Telegram HTML | `SafeHTML` util everywhere |
| Docker NLTK data pain | Container downloads models on build | Layered caching |

---

## 9  Roadmap Beyond 2.0 (Stretch)
- Multi-workspace (Slack, Teams) adapters.  
- On-device embedded vector store for personalised ranking.  
- Voice summarisation (TTS) for mobile.

---

## 10  Glossary
**Digest** – A bundled set of email summaries.  
**Urgency Score** – 0-1 numeric likelihood user must act soon.  
**Plugin** – Drop-in package extending core through event hooks.  
