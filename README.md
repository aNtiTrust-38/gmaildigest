# Gmail Digest Assistant

A smart email companion that helps manage your Gmail inbox by creating summarized digests and providing intelligent notifications through Telegram.

---

## Quick Start
1. Clone the repo and `cd` into the directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -c "import nltk; nltk.download('punkt')"
   ```
4. Run the setup tool:
   ```bash
   python setup_config.py
   ```
5. Start the app:
   ```bash
   python gmaildigest.py
   ```

---

## Requirements
- Python 3.8 or higher (tested on 3.8–3.13)
- pip (Python package manager)
- Tkinter (usually included with Python, required for the setup GUI)
- System packages for cryptography and sumy (on macOS: `brew install libffi` if needed)
- **NLTK** (for summarization):
  - Install with: `pip install nltk`
  - Download punkt: `python -c "import nltk; nltk.download('punkt')"`
- **Google Calendar API** (for calendar integration):
  - Enable the Calendar API in your Google Cloud project
  - Ensure your OAuth credentials include the Calendar scope

## Setup Instructions

### 1. Google Cloud Project Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Gmail API
   - Google Calendar API

### 2. OAuth 2.0 Credentials

1. In the Google Cloud Console, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Desktop app" as the application type
4. Name your client ID (e.g., "Gmail Digest Assistant")
5. Download the credentials JSON file
6. Keep this file secure - you'll need it during setup

### 3. Environment Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -c "import nltk; nltk.download('punkt')"
   ```

3. Run the configuration GUI:
   ```bash
   python setup_config.py
   ```
   
   This will open a user-friendly setup tool that will:
   - Allow you to select your credentials.json file
   - Collect your Telegram bot token
   - Set your forwarding email address
   - Configure the check interval for emails
   - Optionally encrypt your .env file for better security
   - If you need to update your configuration later, simply re-run `python setup_config.py` and overwrite the existing .env file.

   ![Setup GUI](setup-gui-screenshot.png)

   The setup tool will create a properly configured `.env` file with:
   ```
   # === Google API Credentials ===
   CREDENTIALS_PATH=credentials.json

   # === Telegram Bot ===
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token

   # === Anthropic API (optional) ===
   ANTHROPIC_API_KEY=your_anthropic_api_key

   FORWARD_EMAIL=your_forward_email@example.com
   CHECK_INTERVAL_MINUTES=15
   ```
   - The `ANTHROPIC_API_KEY` is **optional**. If omitted, the application will use local summarization (Sumy) for email digests. If provided, advanced AI summarization (Anthropic Claude) will be used.
   - The setup tool and application will work for all users, regardless of whether they have an Anthropic API key.

### 4. Encrypted Configuration (Optional)
If you choose to encrypt your configuration:
- You'll be prompted to create an encryption password
- Your .env file will be encrypted to protect sensitive data
- A `load_env.py` script will be created to handle decryption
- **How to use encrypted configuration:**
  - When you run `python gmaildigest.py`, the app will detect if the .env is encrypted and prompt you for your password automatically.
  - Alternatively, you can run `python load_env.py` to load environment variables before running the main app.

### 4. Telegram Bot Integration

#### Creating a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Start a conversation with BotFather and send the command `/newbot`
3. Follow the prompts to name your bot:
   - Enter a display name (e.g., "Gmail Digest Assistant")
   - Enter a username (e.g., "gmail_digest_bot") - must end with "bot"
4. Once created, BotFather will provide a token that looks like this:
   ```
   123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
   ```
5. Copy this token and add it to the setup tool when prompted

#### Bot Privacy Settings

For handling email data securely, configure these recommended privacy settings:

1. Send `/mybots` to BotFather
2. Select your bot
3. Select "Bot Settings" > "Group Privacy"
4. Enable privacy mode to ensure the bot only responds to commands explicitly directed to it
5. Go to "Bot Settings" > "Allow Groups?" and set according to your needs:
   - For personal use only: Select "Disable"
   - For group usage: Select "Enable"

#### Adding the Bot to Channels/Groups

**For Personal Use:**
1. Search for your bot's username in Telegram
2. Start a conversation by clicking "Start"
3. The bot will now be able to send you digests and notifications

**For Group Chats:**
1. Open the group chat
2. Click the group name at the top
3. Select "Add members"
4. Search for your bot's username and add it
5. Send `/start` in the group to initialize the bot

**For Channels:**
1. Open the channel
2. Click the channel name
3. Select "Administrators"
4. Click "Add Administrator"
5. Search for your bot's username and add it
6. Give it the permission to "Post Messages"
7. Send `/start` in the channel to initialize the bot

#### Available Commands and Button Interface

The Gmail Digest Assistant supports both text commands and an interactive button interface:

**Text Commands:**
- `/start` - Initialize the bot and start scheduled digests
- `/digest` - Get immediate email digest
- `/set_interval <hours>` - Set digest interval (0.5-24 hours)
- `/mark_important <email>` - Mark sender as important
- `/settings` - View current settings
- `/toggle_notifications` - Enable/disable real-time notifications
- `/stop` - Stop all digests and notifications for your chat
- `/restart` - Restart digests and notifications for your chat

**Button Interface:**
- Digest actions are now grouped into two rows for better readability:
  - First row: ⭐ Mark Important, 📤 Forward, 🚫 Leave Unread, ➡️ Next Email
  - Second row: 📅 Add to Calendar
- Main menu with buttons for all primary functions
- Settings screen with toggle buttons
- Digest interval selection with preset options
- One-click actions for important emails
- Navigation buttons for moving between screens

The button interface eliminates the need to remember commands and provides a more user-friendly experience, especially on mobile devices.

#### Troubleshooting

**Bot Not Responding:**
- Ensure the application is running (`python gmaildigest.py`)
- Check that your Telegram token is correct in the `.env` file
- Try restarting the bot with `/start`

**Missing Notifications:**
- Verify notifications are enabled in settings
- Check that the bot has permission to send messages
- Ensure the application has proper internet connectivity

**Authentication Issues:**
- Check that `token.pickle` exists in your project directory
- Delete `token.pickle` and re-authenticate if needed

**Anthropic API Issues & Summarization Fallback:**
- If you do not provide an Anthropic API key, the app will use local summarization (Sumy) for email digests.
- If your Anthropic API key is invalid or rate-limited, the app will automatically fall back to local summarization and log a warning.
- Example output with Anthropic API:
  > "[AI] Project update: Key milestones achieved. Next steps: finalize report by Friday. Action: Review attached files."
- Example output with local summarization:
  > "Project update: milestones achieved. Finalize report by Friday. Review attached files."

**GUI Fails to Launch:**
- Ensure Tkinter is installed. On macOS, you may need to run `brew install python-tk`.

**Summarization Errors:**
- If you see errors related to summarization, check that `sumy` is installed (`pip install sumy`).
- For Anthropic API errors, check your API key and internet connection.

**Updating Configuration:**
- To change your credentials, Telegram token, or other settings, re-run `python setup_config.py` and follow the prompts.
- You can also manually edit the `.env` file if you prefer.

**Digest KeyError (chat_id):**
- If you see a KeyError for your chat_id when requesting a digest, it means the bot lost its in-memory settings (e.g., after a restart or if /start was not run). This is now handled automatically, but always run /start at least once after adding the bot or after a restart.

**Telegram HTML Parse Error ('Can't parse entities', 'unsupported start tag'):**
- If you see an error like 'Can't parse entities: unsupported start tag ...' from Telegram, it means your digest contains unescaped < or > characters (e.g., email addresses or names in angle brackets). This is now fixed by escaping all dynamic content before sending. If you modify the code, always escape user/content data when using parse_mode='HTML'.

**Telegram Message_too_long Error:**
- If you see a 'Message_too_long' error from Telegram, your digest exceeded the 4096 character limit. This is now fixed by splitting long digests into multiple messages. In the future, users will be able to select the digest range (e.g., only new items, last 24h, last week, all inbox) via the setup tool or settings menu.

### Manual Calendar Integration (v0.5)
- Calendar events are only created manually by clicking the "Add to Calendar" button in the digest.
- There is no automatic event detection, parsing, or conflict detection in v0.5.
- Future versions will add more advanced calendar features (see Known Limitations & Roadmap).

### Known Limitations & Roadmap
- "Don't Add" button for calendar-relevant emails is not present in v0.5 (future roadmap).
- Calendar event conflict detection and tagging (**CONFLICT** in event title/description) is not implemented in v0.5.
- Event parsing from emails and showing overlapping event details is not implemented in v0.5.
- Reading time estimation, ML urgency detection, and enhanced calendar integration are planned for future versions.
- See `.cursor/scratchpad.md` or [CHANGES.md](CHANGES.md) for the full roadmap.

### Testing
- To run unit tests:
  ```bash
  pytest tests/unit
  ```
- Integration testing is best done live (send test emails, trigger digests, and observe Telegram output).
- Please report issues via GitHub or email.

## Security Notes

- The `credentials.json` file contains your OAuth client ID and secret
- The `token.pickle` file contains your access tokens
- Never commit these files to version control
- Use `.gitignore` to exclude sensitive files
- Be mindful of who has access to your Telegram bot conversations
- Consider using the encryption option for additional security
- Your Anthropic API key (if used) should be kept private and never shared.

## FAQ
**Q: Can I use this with multiple Gmail accounts?**
A: Not in v0.5. Multi-account support is a planned feature.

**Q: What if I lose my .env encryption password?**
A: You will need to re-run the setup tool and re-authenticate. The encrypted .env cannot be recovered without the password.

**Q: Can I use this bot in a group or channel?**
A: Yes, follow the instructions above for adding the bot to groups or channels. Make sure to configure privacy settings as needed.

**Q: What happens if I change my Google or Telegram credentials?**
A: Re-run `python setup_config.py` to update your configuration.

**Q: How do I get help or report a bug?**
A: Open an issue on GitHub or email the maintainer.

## Features

- OAuth 2.0 authentication for secure access
- Periodic email digests (customizable interval)
- Real-time notifications for important emails
- Interactive button interface for easy navigation
- Smart urgency detection with deadline recognition
- Automatic email forwarding for important messages
- Telegram bot interface for easy management
- Secure, encrypted configuration storage

## License

MIT License

## Anthropic API Key (Optional)
If you want to use advanced AI summarization (Claude), you will need an Anthropic API key.
- Sign up or log in at: https://console.anthropic.com/
- Go to the API Keys section in your Anthropic account dashboard.
- Click "Create Key" and copy the generated API key.
- Paste this key into the "Anthropic API Key (optional)" field in the setup GUI.
- If you do not have an API key, leave this field blank to use local summarization instead.

## Changelog
See [CHANGES.md](CHANGES.md) for a history of major improvements and iterations.

### Digest Formatting and Summarization
- Each email digest entry now displays:
  - Sender
  - Subject (truncated to 200 characters if needed)
  - Suggested Urgency (🟢 Normal, 🔴 Urgent, ⭐ Important)
  - Summary: A single concise paragraph, less than 500/1000 characters, focusing only on essential information (no subject/body labels, no links or images).

### Summarization Robustness
- The assistant uses a tiered summarization strategy:
  1. **Anthropic API (Claude):** Used if available and not rate-limited.
  2. **Local Summarizer (Sumy):** Used if the API is unavailable or rate-limited.
  3. **Heuristic Fallback:** If both fail, uses the first few sentences of the email body or the subject.
- The digest will indicate if a local or fallback summary was used (e.g., '[Local summary]', '[Fallback summary]').

## Interactive Digest Navigation

- When you use /digest, only unread emails in your inbox are shown (using the Gmail filter `is:unread in:inbox`).
- Below each summary are four inline buttons:
  - ⭐ Mark as Important: Mark the sender as important for future digests.
  - 📤 Forward: Forward the email to your configured address (the email will also be marked as read and archived, so it won't remain in your inbox).
  - 🚫 Leave Unread: Skip to the next email without marking this one as read or archiving it.
  - ➡️ Next Email: Mark this email as read, archive it, and show the next email in the digest.
- After you click any action, the next email is automatically shown (with confirmation if applicable).
- This ensures you never lose the action buttons as you review your emails, and you can control which emails are marked as read and archived. 