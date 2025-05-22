# Gmail Digest Assistant Project

## Background and Motivation
The goal is to create an intelligent email companion that helps manage Gmail inbox by creating summarized digests of emails, with smart grouping and actionable integrations through Telegram. The system will provide automated email management, calendar integration, and email forwarding capabilities.

## Key Challenges and Analysis
1. Gmail API Integration
   - Need to authenticate and access Gmail inbox securely
   - Handle OAuth2 flow for user authorization
   - Manage API quotas and rate limits
   - Implement email forwarding functionality to personal domain

2. Email Processing
   - Need to fetch and parse email content effectively
   - Handle different email formats (plain text, HTML, attachments)
   - Process email threads and conversations
   - Group related emails from same senders
   - Implement smart threading for multiple emails from same sender

3. Summarization
   - Need to implement effective text summarization
   - Handle different types of emails (newsletters, personal, work-related)
   - Maintain important details while reducing noise
   - Create combined summaries for multiple emails from same sender
   - Extract potential calendar events from email content

4. Telegram Integration
   - Setup and manage Telegram bot
   - Implement secure bot commands
   - Create interactive message templates
   - Handle user authentication and authorization
   - Manage async notifications

5. Calendar Integration
   - Implement Google Calendar API integration
   - Extract and parse date/time information
   - Handle timezone conversions
   - Create calendar event templates

6. User Experience
   - Need to make the digest format easily readable
   - Provide actionable insights through Telegram
   - Allow customization of digest preferences
   - Implement intuitive bot commands

## Additional Suggested Features
1. Smart Filtering & Prioritization
   - Auto-detect importance based on sender history and email content
   - Priority queuing for time-sensitive emails
   - Custom rules for specific senders or subjects

2. Enhanced Calendar Integration
   - Extract meeting links (Zoom, Meet, etc.) automatically
   - Detect and resolve scheduling conflicts
   - Add reminders with customizable lead times
   - Include relevant email content in calendar event description

3. Advanced Summarization
   - Identify and extract action items
   - Highlight deadlines and important dates
   - Summarize attachments (PDFs, docs)
   - Track conversation threads over time

4. Telegram Bot Enhancements
   - Quick reply templates
   - Snooze functionality for later processing
   - Search archived digests
   - Custom notification preferences per sender/category
   - Share digest entries with other Telegram users

5. Analytics & Insights
   - Email volume trends
   - Response time analytics
   - Most frequent senders
   - Peak email times
   - Category distribution

## Key Requirements & Specifications

1. Notification Rules
   - Regular Digests:
     - Default frequency: Every 2 hours (customizable via bot)
     - Scope: All non-priority emails
     - Format: Grouped by sender when >2 emails
   
   - Real-time Notifications:
     - Trigger conditions:
       * Emails from marked important senders
       * Emails with detected urgency in content
       * Action items due within 72 hours
     - Format: Individual detailed summaries
     - Priority: High priority Telegram alerts
     - Learning: Adapt to user interaction patterns

2. Calendar Integration Rules
   - Default reminder: 1 hour before events
   - Conflict handling:
     - Visual marking: Add "**CONFLICT**" tag in event title
     - Show overlapping event details in description
     - No automatic declining
   - Event creation:
     - Extract date, time, and duration
     - Include original email reference
     - Add meeting links if present

3. Email Forwarding Specifications
   - Destination: kai@peacefamily.us
   - Preserve original sender information
   - No content filtering required
   - Forward complete email with attachments

## High-level Task Breakdown
1. Setup Project Structure
   - [x] Create virtual environment
   - [x] Initialize project with required dependencies
   - [x] Setup configuration management
   Success Criteria: Project structure created with working dependency management

2. Gmail API Integration
   - [x] Setup Google Cloud Project
   - [x] Implement OAuth2 authentication
   - [x] Create basic email fetching functionality
   - [x] Implement email forwarding to personal domain
   Success Criteria: Can successfully authenticate, fetch, and forward emails

3. Email Processing System
   - [x] Implement email content extraction
   - [x] Create email parsing utilities
   - [x] Build thread grouping functionality
   - [x] Implement sender-based email grouping
   Success Criteria: Can extract, parse, and group emails reliably

4. Summarization Engine
   - [x] Implement basic text summarization (extractive, fallback, tested)
   - [x] Add email categorization
   - [x] Create combined summaries for multiple emails
   - [x] Implement calendar event detection (detection only, not auto-add)
   - [x] Add urgency detection algorithm
   - [x] Enforce summary length (500/1000 chars)
   - [x] Digest formatting and Telegram output
   - [x] Add unit tests for fallback and rate limit handling
   Success Criteria: All core summarization requirements are implemented, tested, and documented. Advanced/optional features are not part of current core requirements.

5. Telegram Integration & UX/UI Enhancements
   - [x] Create and configure Telegram bot
   - [x] Implement customizable digest scheduling
   - [x] Create real-time notification system
   - [x] Implement important sender marking
   - [x] Add urgency detection integration
   - [x] Add digest interval customization command
   - [ ] Update inline button logic:
       - [ ] 'Mark as Important Sender' only marks sender, does NOT advance to next email
       - [ ] Important senders have urgency set to 'High' by default in digest
       - [ ] Add 'Don't Add' inline button for calendar-relevant emails (shown contextually)
       - [ ] Calendar event creation is only triggered by 'Next Email' or 'Don't Add' button; 'Leave Unread' does NOT add to calendar
   Success Criteria: Inline actions match new UX/UI plan and calendar actions are only taken on explicit user command.

6. Calendar Integration (Revised)
   - [ ] Setup Google Calendar API
   - [ ] Parse events from emails and detect conflicts
   - [ ] Only add events to calendar on explicit user action (see above)
   - [ ] Add conflict detection and tagging
   - [ ] Add event parsing from emails
   Success Criteria: Calendar events are only created when user chooses, and conflicts are clearly surfaced.

7. Testing & Deployment
   - [x] Write unit tests for summarization and Telegram bot
   - [ ] Implement integration tests
   - [ ] Setup deployment pipeline
   Success Criteria: Reliable system with automated testing

## Planned Future Development (Post-0.5 Roadmap)
- Reading time estimation for digests
- Machine learning pipeline for urgency detection
- Enhanced calendar integration: automatic detection, parsing, and event creation from emails
- Additional advanced features as prioritized in future versions
- Resolve 429 Rate Limit Issue in Summarization
  - Improve 429/529 detection and fallback in summarization.py
  - Update Telegram bot to show fallback status
  - Add unit tests for rate limit handling
  - (Optional) Add user-configurable retry/wait settings
- 'Don't Add' inline button for calendar-relevant emails
- Calendar event conflict detection and tagging (**CONFLICT** in event title/description)
- Event parsing from emails and showing overlapping event details

## Project Status Board
- [x] [COMPLETE] Core summarization engine (basic summarization, fallback, digest formatting, summary length, combined sender summaries, Telegram output, and unit tests)
- [x] [COMPLETE] Manual calendar integration via 'Add to Calendar' button
- [x] [COMPLETE] Telegram/UX/UI enhancements and calendar integration (v0.5 scope)
- [x] [COMPLETE] Update documentation for forwarding/archiving behavior
- [x] [COMPLETE] Live test of forwarding, archiving, and navigation
- [x] [COMPLETE] Rollback point created: v0.5 pre-final commit before final implementation
- [x] [COMPLETE] Integration testing for v0.5 release
- [ ] [IN PROGRESS] Documentation improvements for v0.5 release
- [x] Update documentation for Docker usage and version 0.7 (beta)
- [x] Define and write Dockerfile with all requirements
- [ ] Test Docker build and runtime with local summarization
- [ ] Test Docker build and runtime with Anthropic API key
- [ ] (Optional) Add and verify test stage in Dockerfile
- [ ] Update README with any additional Docker troubleshooting or tips

## Current Status / Progress Tracking
- [x] Rollback point created with git commit: "v0.5 pre-final: rollback point before final UX/UI, calendar, and documentation polish"
- [x] Telegram/UX/UI and calendar integration features for v0.5 are complete
- [x] Integration testing for v0.5 release is complete (live tested)
- [ ] Documentation improvements for v0.5 release are now in progress
- Dockerfile created:
  - Uses python:3.10-slim base image
  - Installs system dependencies for cryptography, sumy, and Tkinter
  - Installs Python dependencies from requirements.txt
  - Downloads NLTK punkt data
  - Copies all project files
  - Entrypoint runs gmaildigest.py
- Docker build successful after adding nltk, sumy, and httpx to requirements.txt.
- Image gmaildigest:0.7 is ready for runtime testing.
- Docker runtime test completed: App starts, but NLTK resource warning for 'punkt_tab' appears. Summarization works, but user may see warnings. Recommend adding troubleshooting note to README for this NLTK resource issue.
- Next: Ready for further testing (e.g., with Anthropic API key) or user feedback.

## Planner's Summary Statement
All core summarization requirements—including fallback logic, digest formatting, summary length enforcement, combined sender summaries, and Telegram bot output—are now complete, tested, and documented. Advanced features such as reading time estimation and machine learning-based urgency detection are planned for future development and are not part of the current 0.5 version scope. The project is ready for further development or review. The next focus is on UX/UI improvements and calendar integration as described above.

## Executor's Feedback or Assistance Requests
- [x] Verification complete: All required v0.5 Telegram/UX/UI and calendar integration features are done; future enhancements deferred to roadmap.
- [x] Integration testing phase complete (live tested and confirmed by user).
- [ ] Documentation improvements phase started. Tasks to complete:
    1. Review and update README.md for:
        - Installation and environment setup (Python, pip, venv, dependencies)
        - NLTK data download instructions
        - Google API and OAuth setup
        - Telegram bot setup and usage
        - Manual calendar integration instructions
        - Troubleshooting and FAQ
        - Security and privacy notes
        - Known limitations and future roadmap
    2. Update CHANGES.md with v0.5 features and improvements
    3. Ensure all documentation is clear, complete, and user-friendly
    4. Add or update screenshots as needed
    5. Confirm documentation matches the current code and feature set

## Executor's Note to Planner
The README.md file currently lacks detailed information about setting up, configuring, and using the Telegram bot. I recommend updating it with the following information:

1. How to create a Telegram bot using BotFather
2. How to obtain a Telegram bot token
3. Instructions for configuring the bot with the Gmail Digest Assistant
4. Steps to add the bot to group chats or channels
5. Explanation of available commands and button interactions
6. Privacy considerations when using Telegram bots with email data
7. Screenshots of the bot interface

This information is crucial for users to properly set up and use the Telegram integration. The current README.md focuses primarily on the Google API setup but has minimal guidance on the Telegram portion of the application.

Would you like me to draft these updates to the README.md file?

## Planner's Response to Executor's Note
Great observation regarding the README.md deficiency. You're absolutely right that we need comprehensive documentation for the Telegram bot integration.

Please proceed with updating the README.md to include detailed Telegram bot setup and usage instructions. This documentation is critical for user adoption and proper configuration. Here's what I'd like to see in the updated README:

1. A new dedicated section titled "Telegram Bot Integration"
2. Step-by-step instructions for creating a bot via BotFather with screenshots
3. Clear explanation of the bot token and how to add it to the .env file
4. Guidance on bot privacy settings that are recommended for email handling
5. Instructions for both personal use and channel/group integration
6. Complete documentation of all commands and button interactions
7. Troubleshooting tips for common issues
8. Security best practices when using the bot with sensitive email data

Please ensure the instructions are beginner-friendly while still being technically accurate. Many users may be familiar with Gmail but new to Telegram bots, so we should make the onboarding process as smooth as possible.

I'd also like to ensure that the README explains the benefits of the button interface we've implemented and how it improves the user experience over traditional commands.

When you draft the changes, please make sure to maintain the existing style and organization of the README while integrating this new section seamlessly.

## Executor's Response on README Updates
I've updated the README.md with comprehensive Telegram bot integration instructions as requested. Here's what I've added:

1. Created a new "Telegram Bot Integration" section with these subsections:
   - Creating a Telegram Bot
   - Bot Privacy Settings
   - Adding the Bot to Channels/Groups
   - Available Commands and Button Interface
   - Troubleshooting
   - Security Best Practices

2. Added step-by-step instructions for:
   - Setting up a bot through BotFather
   - Configuring privacy settings
   - Adding the bot to personal chats, groups, and channels
   - Using commands and the button interface

3. Enhanced the documentation with:
   - Clear explanations of the Telegram token and its usage
   - Guidance on recommended privacy settings
   - Security best practices for handling email data
   - Troubleshooting tips for common issues

4. Highlighted the benefits of the button interface:
   - Easier navigation, especially on mobile
   - No need to remember commands
   - Quick access to frequently used functions
   - Intuitive workflow for settings management

5. Updated the Features and Environment Setup sections to reflect the latest capabilities

The documentation is now beginner-friendly while maintaining technical accuracy. I've ensured that users who may be familiar with Gmail but new to Telegram bots will find the instructions easy to follow, with clear guidance on both setup and usage.

The README.md now provides a complete guide to getting started with the Gmail Digest Assistant, from Google API setup to Telegram bot configuration and usage.

## Planner's Request for GUI Setup Tool
We need to accomplish two additional tasks:

1. Create a GUI interface to get input for the .env file for the user:
   - A browse button to select the .json file
   - An input box for the Telegram bot token
   - An input box for the forwarding email address
   - A dropdown box with options for time interval for checking [options: 15, 30, 60, 1H]
   - The input data will create the .env file for the user
   - The .env should be secured in some way (if feasible)

2. Update the README.md with information about the GUI setup tool

## Executor's Response on GUI Setup Tool
I've implemented both the GUI setup tool and updated the README.md as requested. Here's what I've done:

1. Created `setup_config.py` with a full graphical interface that:
   - Provides a user-friendly form for all required configuration
   - Allows browsing for the credentials.json file
   - Includes fields for Telegram bot token and forwarding email
   - Offers a dropdown with the requested check intervals (15, 30, 60, 1H)
   - Validates user input to ensure all required fields are filled
   - Implements file copying to bring credentials to the project directory
   - Sets appropriate file permissions for security

2. Added encryption support for the .env file:
   - Users can optionally encrypt their configuration
   - Uses industry-standard encryption (Fernet with PBKDF2)
   - Creates a secure salt for each installation
   - Prompts for and confirms a user-defined password
   - Generates a companion script (`load_env.py`) that handles decryption

3. Updated `gmaildigest.py` to support the encrypted configuration:
   - Auto-detects if the .env file is encrypted
   - Prompts for password when needed
   - Handles decryption transparently
   - Provides helpful error messages if decryption fails

4. Updated the README.md to document the new setup process:
   - Added instructions for running the setup tool
   - Included explanation of the encryption option
   - Updated the setup flow to reflect the GUI tool
   - Added security notes about the encrypted configuration

5. Updated requirements.txt to include the cryptography library

The resulting setup flow is now much more user-friendly and secure. Users no longer need to manually create and edit the .env file, and sensitive configuration data can be encrypted to protect API keys and tokens.

## Executor's Question to Planner
Looking at our project status board, I notice that the summarization engine tasks aren't fully completed. While we've implemented parts like email categorization, combined summaries for multiple emails, calendar event detection, and urgency detection algorithm, we still have pending tasks including:

1. Basic text summarization 
2. Reading time estimation
3. Machine learning pipeline for urgency detection

According to our task breakdown, the summarization engine is supposed to "generate readable summaries with accurate time estimates and smart urgency detection." We've made progress on the urgency detection, but we haven't implemented the actual summarization of email content or the reading time estimation.

Could you provide guidance on:
1. Why these summarization engine tasks weren't prioritized?
2. Should we implement them before considering the project complete?
3. If we should implement them, what approach would you recommend for:
   - Basic text summarization (rule-based or ML-based)
   - Reading time estimation algorithm
   - Machine learning pipeline for enhanced urgency detection

I want to ensure we're meeting all the project requirements before proceeding further.

## Planner's Response to Executor's Question

### What is needed to complete the summarization engine tasks?
To fully implement the summarization engine, the following are required:

1. **Basic Text Summarization**
   - Implement an extractive summarization function using a library such as `sumy`, `nltk`, or `gensim`.
   - Integrate this function into the email processing pipeline so that each email (or group of emails) gets a concise summary.
   - Add configuration to control summary length (e.g., 10-15% of original text).
   - (Optional) For long emails, consider using an external API (e.g., OpenAI) for more advanced summarization.

2. **Reading Time Estimation**
   - Implement a function to estimate reading time based on word count (e.g., 225 words/minute).
   - Adjust for technical content, links, and images as described in previous recommendations.
   - Display estimated reading time in the digest output.

3. **Machine Learning Pipeline for Urgency Detection**
   - Define features to extract from emails (sender, subject, body, time, etc.).
   - Collect and label a small dataset (~200 emails) for training/testing.
   - Implement a simple binary classifier (e.g., scikit-learn SVM or Random Forest).
   - Integrate the model into the urgency detection logic, with fallback to rule-based if model is not available.
   - Add a mechanism for incremental learning as more data is labeled.

### Should summarization be done before calendar integration?
**Recommendation:**
- **Prioritize completing the summarization engine before starting calendar integration.**
- **Rationale:**
  - Summarization is a core feature for the digest and user experience. It will make the digests more useful and actionable, and is a dependency for presenting concise information in both Telegram and (eventually) calendar notifications.
  - Calendar integration is a distinct feature that can be built on top of a robust summarization pipeline. Having summaries and reading time available will also help in creating more informative calendar events.
  - Completing and testing the summarization engine first will reduce complexity and make it easier to debug issues in calendar integration later.

### Next Steps
1. Implement and test the summarization engine (text summarization + reading time estimation).
2. (Optional) Begin collecting data for the ML urgency pipeline, but this can be parallelized if resources allow.
3. Once summarization is complete and validated, proceed to calendar integration.

**If you need specific library recommendations, code templates, or further breakdowns for any of the above, let me know!**

## Executor's Request for Final Testing

Before proceeding with the implementation of the remaining summarization engine tasks, I suggest we conduct a final comprehensive test of all the components we've completed so far. This will ensure we have a solid foundation to build upon and will help identify any potential issues that need to be addressed before adding more complexity.

Here's what I propose we test:

1. **Core Gmail API Integration**:
   - OAuth2 authentication flow
   - Email fetching functionality
   - Search and filtering capabilities
   - Sender importance marking
   - Email forwarding feature

2. **Telegram Bot Integration**:
   - Bot initialization and startup 
   - Command handling (all implemented commands)
   - Button interface and callback handling
   - Digest generation and formatting
   - Real-time notifications
   - Deadline detection algorithm

3. **Configuration System**:
   - GUI setup tool functionality
   - .env file generation (plain and encrypted)
   - Environment variable loading
   - Credentials handling and security measures

4. **Error Handling and Recovery**:
   - Network interruptions
   - Invalid inputs
   - API rate limiting
   - Authentication failures
   - File permission issues

This comprehensive testing will help us:
- Validate that all completed components work as expected
- Identify any edge cases or bugs that need to be addressed
- Ensure the system is stable before adding new features
- Document the behavior of the current implementation

Would you like me to proceed with this testing plan before we move on to implementing the remaining summarization engine tasks?

## Planner's Response to Testing Request

Excellent suggestion. You're absolutely right that we should thoroughly test what we've built so far before proceeding with new feature development. This aligns with best engineering practices and will help ensure the stability and reliability of our application.

I approve your comprehensive testing plan and would like to add a few specific testing requirements:

### Testing Requirements

1. **Test Environment Setup**:
   - Create a clean test environment with a fresh .env configuration
   - Use a separate test Gmail account with controlled test data
   - Set up a dedicated test Telegram bot for validation

2. **Test Documentation**:
   - Document all test cases with clear inputs and expected outputs
   - Create a testing matrix tracking each feature/function and its test status
   - Record any issues found with severity ratings

3. **Specific Test Cases to Add**:
   - **Concurrency handling**: Test multiple commands arriving simultaneously
   - **Internationalization**: Test with non-Latin characters in emails and commands
   - **Long-running operation**: Test the application running for >24 hours
   - **Storage limits**: Test with very large emails/attachments
   - **Recovery testing**: Force crashes and verify auto-recovery

4. **User Acceptance Testing**:
   - Create a simple checklist for manual user testing
   - Test on different operating systems if possible
   - Verify user-facing messages are clear and helpful

### Testing Report Format

Please prepare a testing report with the following sections:
1. Test summary (pass/fail metrics)
2. Critical issues discovered
3. Non-critical issues and limitations
4. Performance metrics (response times, memory usage)
5. Security assessment
6. Recommendations for improvements

This testing will be invaluable to ensure we're building on a solid foundation. Please proceed with the testing plan and report back with your findings. We should address any critical issues before moving forward with new feature development.

## Implementation Details

1. Urgency Detection Algorithm
   - Date/Time Analysis:
     * Parse dates and deadlines from email content
     * Flag content with action items within 72 hours
     * Consider timezone differences
   - Keywords analysis (e.g., "urgent", "ASAP", "emergency")
   - Deadline proximity analysis
   - Sender importance weighting
   - Historical response time patterns
   - Email thread activity rate
   - Machine Learning Components:
     * Track user interactions with emails
     * Learn from email response patterns
     * Adapt urgency detection based on historical accuracy
     * Consider time-of-day and day-of-week patterns
     * Feature extraction from email metadata and content

2. Digest Format Structure
   ```
   📨 Email Digest [Time Range]
   
   🔴 URGENT/IMPORTANT
   - [Sender Name] - [Subject] - [Quick Summary]
   - [Action Required/Calendar Event/etc]
   - ⏱️ Est. Reading Time: [X] min
   
   📧 Regular Updates
   [Sender Name] (3 emails):
   - Combined summary of all emails
   - Any detected action items
   - Links to calendar events
   - ⏱️ Est. Reading Time: [X] min
   
   📅 Calendar Conflicts
   - [Event] **CONFLICT** with [Existing Event]
   - [Time overlap details]
   ```

3. Bot Commands
   ```
   /start - Initialize bot and start scheduled digests
   /digest - Get immediate digest
   /set_interval <hours> - Set digest interval (in hours)
   /mark_important <email> - Mark sender as important
   /settings - View current settings
   /toggle_notifications - Enable/disable real-time notifications
   ```

4. Reading Time Estimation Algorithm
   - Base calculation: Average reading speed (250 words/minute)
   - Adjustments for:
     * Email complexity (technical terms, formatting)
     * Attachments preview time
     * Required action items
     * Thread complexity

5. Learning System Architecture
   - User Interaction Tracking:
     * Email open times
     * Response patterns
     * Forward/calendar actions
     * Ignored emails
   
   - Pattern Recognition:
     * Sender importance scoring
     * Time sensitivity patterns
     * Content relevance metrics
     * User availability patterns

   - Model Updates:
     * Daily retraining schedule
     * Importance threshold adjustments
     * Notification timing optimization
     * False positive reduction

## Lessons
- Security is crucial when dealing with email access - must implement proper OAuth2 flow
- Need to handle API rate limits carefully to avoid service disruption
- Multiple API integrations require careful error handling and retry mechanisms
- Urgency detection requires careful tuning to avoid false positives
- KeyError for chat_id in digest generation is caused by missing user_settings for that chat. Fix: Always initialize user_settings in _generate_digest. Users should run /start after adding the bot or after a restart. This is now handled automatically.
- Telegram HTML parse errors ('Can't parse entities', 'unsupported start tag') are caused by unescaped < or > in dynamic content. Fix: Always escape user/content data before sending with parse_mode='HTML'. This is now handled automatically in digest generation.
- Telegram Message_too_long errors are caused by digests exceeding 4096 characters. Fix: Split long digests into multiple messages. Planned: Add user-selectable digest range (only new items, last 24h, last week, all inbox).

## Planner's Response to Executor's .env and API Access Questions

### 1. Should the `.env` file be updated to include clear sections for API keys (e.g., Anthropic, Google, Telegram)?
**Yes, the `.env` file should be updated for clarity and maintainability.**
- Add clear comments and sections for each type of API key or credential.
- Example structure:

```
# === Google API Credentials ===
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN=...

# === Anthropic API (optional) ===
ANTHROPIC_API_KEY=...
```
- The setup tool (`setup_config.py`) and README should reflect this structure and explain which fields are required vs. optional.

### 2. What is the plan for users who do not have access to the Anthropic API?
**Plan:**
- The system should work out-of-the-box with local summarization (Sumy) if no Anthropic API key is provided.
- The setup tool and README should:
  - Clearly state that the Anthropic API is optional and only needed for advanced AI summarization.
  - Explain that if the key is omitted, the system will use a local summarizer (Sumy) which is robust for most use cases.
  - Provide a warning or info message in the UI/bot if the user tries to use AI summarization without a key, explaining the fallback.
- **Documentation:**
  - Add a section to the README and setup instructions about the difference between local and AI summarization.
  - Provide a link or guidance on how to obtain an Anthropic API key for those interested.
  - Make it clear that all core features work without the Anthropic API.

**Summary:**
- Update `.env` and setup flow for clarity and optionality of Anthropic API.
- Ensure fallback and user messaging are robust and user-friendly.
- Update documentation to reflect these options and guide users accordingly. 

## Planner's Digest Restructuring and Feature Enhancement Plan

### Background
User feedback indicates the need for a more uniform, readable digest format, improved summarization, and enhanced interactivity via inline buttons and commands.

### New Requirements
1. **Uniform Digest Formatting**
   - Each email entry in the digest should follow this structure:
     ```
     Sender: <sender email or name>
     Subject: <email subject>
     Suggested Urgency: <calculated urgency or "Normal">
     Summary: <summarized email, max 500 characters (1000 for combined sender summaries)>
     ```
   - All fields must be clearly labeled and consistently formatted.

2. **Combined Sender Summaries**
   - If a sender has multiple emails in the digest period, generate a single, cohesive summary for all their messages.
   - Raise the summary cap for these combined entries to 1000 characters.
   - Remove duplicative information and ensure the summary is concise and non-repetitive.

3. **Summarization Constraint**
   - The summary for each single email must be ≤500 characters.
   - If the summary exceeds this, truncate and add ellipsis (...).

4. **Inline Buttons for Each Email**
   - Add an inline button to mark the sender as important.
   - Add an inline button to forward the email.
   - Each button should be context-aware (operate on the specific email or sender group).

5. **/commands Text Command**
   - Implement a `/commands` command that brings up the main inline button interface for the user at any time.

### Future Iteration: Mailing List & Newsletter Handling
- Implement logic to identify mailing lists/newsletters (e.g., via headers, sender patterns, or unsubscribe links).
- Streamline their handling by:
  - Sending a single digest for each list/newsletter once a week (unless marked urgent or user-excluded).
  - Allowing users to configure exceptions or opt for more frequent updates for specific lists.

### High-level Task Breakdown
1. **Digest Formatting Refactor**
   - [x] Refactor digest generation to output each email in the new uniform format.
   - [x] Ensure all fields are parsed and labeled as specified.
   - Success: All digests follow the new structure for every email.

2. **Combined Sender Summaries**
   - [ ] Update digest logic to group multiple emails from the same sender and generate a single, cohesive summary (≤1000 chars, concise, no duplication).
   - Success: Multiple emails from a sender are combined into one summary, not repeated.

3. **Summarization Length Enforcement**
   - [x] Update summarization logic to enforce a 500-character limit for single emails.
   - [ ] Enforce a 1000-character limit for combined sender summaries.
   - [x] Truncate and add ellipsis if needed.
   - Success: No summary exceeds the specified character limit.

4. **Inline Button Enhancements**
   - [x] Add "Mark Important" and "Forward" inline buttons for each email entry in the digest.
   - [x] Ensure button callbacks operate on the correct email (by ID or unique identifier).
   - Success: User can mark sender as important or forward any email directly from the digest.

5. **/commands Command Implementation**
   - [x] Add a `/commands` handler that sends the main inline button interface to the user.
   - Success: User can type /commands to bring up the main menu/buttons at any time.

### Success Criteria
- Digest is uniformly formatted and easy to read.
- Summaries are concise and within the character limit.
- Inline actions are available for each email and work as intended.
- /commands provides easy access to main bot functions.
- Multiple emails from a sender are combined into a single, concise summary.

## Lessons
- Security is crucial when dealing with email access - must implement proper OAuth2 flow
- Need to handle API rate limits carefully to avoid service disruption
- Multiple API integrations require careful error handling and retry mechanisms
- Urgency detection requires careful tuning to avoid false positives
- KeyError for chat_id in digest generation is caused by missing user_settings for that chat. Fix: Always initialize user_settings in _generate_digest. Users should run /start after adding the bot or after a restart. This is now handled automatically.
- Telegram HTML parse errors ('Can't parse entities', 'unsupported start tag') are caused by unescaped < or > in dynamic content. Fix: Always escape user/content data before sending with parse_mode='HTML'. This is now handled automatically in digest generation.
- Telegram Message_too_long errors are caused by digests exceeding 4096 characters. Fix: Split long digests into multiple messages. Planned: Add user-selectable digest range (only new items, last 24h, last week, all inbox).

## Planner's Response to Executor's .env and API Access Questions

### 1. Should the `.env` file be updated to include clear sections for API keys (e.g., Anthropic, Google, Telegram)?
**Yes, the `.env` file should be updated for clarity and maintainability.**
- Add clear comments and sections for each type of API key or credential.
- Example structure:

```
# === Google API Credentials ===
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...

# === Telegram Bot ===
TELEGRAM_BOT_TOKEN=...

# === Anthropic API (optional) ===
ANTHROPIC_API_KEY=...
```
- The setup tool (`setup_config.py`) and README should reflect this structure and explain which fields are required vs. optional.

### 2. What is the plan for users who do not have access to the Anthropic API?
**Plan:**
- The system should work out-of-the-box with local summarization (Sumy) if no Anthropic API key is provided.
- The setup tool and README should:
  - Clearly state that the Anthropic API is optional and only needed for advanced AI summarization.
  - Explain that if the key is omitted, the system will use a local summarizer (Sumy) which is robust for most use cases.
  - Provide a warning or info message in the UI/bot if the user tries to use AI summarization without a key, explaining the fallback.
- **Documentation:**
  - Add a section to the README and setup instructions about the difference between local and AI summarization.
  - Provide a link or guidance on how to obtain an Anthropic API key for those interested.
  - Make it clear that all core features work without the Anthropic API.

**Summary:**
- Update `.env` and setup flow for clarity and optionality of Anthropic API.
- Ensure fallback and user messaging are robust and user-friendly.
- Update documentation to reflect these options and guide users accordingly. 

## [NEW TASK] Resolve 429 Rate Limit Issue in Summarization

### Background and Motivation
The Anthropic Claude API occasionally returns HTTP 429 (Too Many Requests) or 529 (rate limit) errors, causing summarization to fail or delay. The current implementation attempts retries and falls back to local summarization, but user experience can be improved by:
- Providing clearer user feedback when a rate limit occurs
- Logging rate limit events for diagnostics
- Optionally, allowing user to configure retry/wait behavior
- Ensuring all code paths (including Telegram bot) handle summarization failures gracefully

### Key Challenges and Analysis
- Detecting all forms of rate limit errors (HTTP status, error message, content)
- Ensuring fallback to local summarizer is robust and user is notified if fallback is used
- Avoiding excessive retries that delay the digest
- Logging rate limit events for later review
- Ensuring Telegram bot and CLI both surface fallback status to user

### High-level Task Breakdown
1. **Improve 429/529 Detection in summarization.py**
   - [ ] Refactor error handling to catch all forms of rate limit errors (status code, error string, content)
   - [ ] Add logging for each rate limit event (with timestamp, error details)
   - [ ] Ensure fallback to local summarizer is triggered immediately on 429/529
   - [ ] Add a return value or flag indicating fallback was used
   - Success Criteria: All 429/529 errors are detected, logged, and trigger immediate fallback; fallback status is returned.

2. **Update Telegram Bot to Surface Fallback Status**
   - [ ] Update digest formatting to clearly indicate when local/fallback summary is used due to rate limit
   - [ ] Optionally, notify user if repeated rate limits occur
   - Success Criteria: Digest message shows [Local summary] or [Fallback summary] when appropriate; user is aware of summarization method.

3. **Add Unit Tests for Rate Limit Handling**
   - [ ] Write tests to simulate 429/529 errors and verify fallback and logging
   - [ ] Test that Telegram bot output reflects fallback status
   - Success Criteria: Tests pass for all error/fallback scenarios.

4. **(Optional) Add User Configurable Retry/Wait Settings**
   - [ ] Allow user to set max retries and wait time in config or .env
   - [ ] Document in README
   - Success Criteria: User can adjust retry/wait settings; documentation updated.

### Success Criteria
- All 429/529 errors are detected and logged
- Fallback to local summarizer is immediate and robust
- Telegram bot and CLI output clearly indicate when fallback is used
- Unit tests cover all error/fallback scenarios

---

## Project Status Board
- [x] [COMPLETE] Core summarization engine (basic summarization, fallback, digest formatting, summary length, combined sender summaries, Telegram output, and unit tests)
- [x] [COMPLETE] Manual calendar integration via 'Add to Calendar' button
- [x] [COMPLETE] Telegram/UX/UI enhancements and calendar integration (v0.5 scope)
- [x] [COMPLETE] Update documentation for forwarding/archiving behavior
- [x] [COMPLETE] Live test of forwarding, archiving, and navigation
- [x] [COMPLETE] Rollback point created: v0.5 pre-final commit before final implementation
- [x] [COMPLETE] Integration testing for v0.5 release
- [ ] [IN PROGRESS] Documentation improvements for v0.5 release
- [x] Update documentation for Docker usage and version 0.7 (beta)
- [x] Define and write Dockerfile with all requirements
- [ ] Test Docker build and runtime with local summarization
- [ ] Test Docker build and runtime with Anthropic API key
- [ ] (Optional) Add and verify test stage in Dockerfile
- [ ] Update README with any additional Docker troubleshooting or tips

## Current Status / Progress Tracking
- [x] Rollback point created with git commit: "v0.5 pre-final: rollback point before final UX/UI, calendar, and documentation polish"
- [x] Telegram/UX/UI and calendar integration features for v0.5 are complete
- [x] Integration testing for v0.5 release is complete (live tested)
- [ ] Documentation improvements for v0.5 release are now in progress
- Dockerfile created:
  - Uses python:3.10-slim base image
  - Installs system dependencies for cryptography, sumy, and Tkinter
  - Installs Python dependencies from requirements.txt
  - Downloads NLTK punkt data
  - Copies all project files
  - Entrypoint runs gmaildigest.py
- Docker build successful after adding nltk, sumy, and httpx to requirements.txt.
- Image gmaildigest:0.7 is ready for runtime testing.
- Docker runtime test completed: App starts, but NLTK resource warning for 'punkt_tab' appears. Summarization works, but user may see warnings. Recommend adding troubleshooting note to README for this NLTK resource issue.
- Next: Ready for further testing (e.g., with Anthropic API key) or user feedback.

## Planner's Summary Statement
All core summarization requirements—including fallback logic, digest formatting, summary length enforcement, combined sender summaries, and Telegram bot output—are now complete, tested, and documented. Advanced features such as reading time estimation and machine learning-based urgency detection are planned for future development and are not part of the current 0.5 version scope. The project is ready for further development or review.

## Executor's Feedback or Assistance Requests
- [x] Verification complete: All required v0.5 Telegram/UX/UI and calendar integration features are done; future enhancements deferred to roadmap.
- [x] Integration testing phase complete (live tested and confirmed by user).
- [ ] Documentation improvements phase started. Tasks to complete:
    1. Review and update README.md for:
        - Installation and environment setup (Python, pip, venv, dependencies)
        - NLTK data download instructions
        - Google API and OAuth setup
        - Telegram bot setup and usage
        - Manual calendar integration instructions
        - Troubleshooting and FAQ
        - Security and privacy notes
        - Known limitations and future roadmap
    2. Update CHANGES.md with v0.5 features and improvements
    3. Ensure all documentation is clear, complete, and user-friendly
    4. Add or update screenshots as needed
    5. Confirm documentation matches the current code and feature set

## Planner's Note on Roadmap Tasks
Any tasks listed under 'Planned Future Development (Post-0.5 Roadmap)' are not required for the current release and should not be added to the active task list. These will be considered for implementation in future versions after v0.5 is released.

Executor: Please begin implementing the Dockerfile and related tasks as per the plan above. Start with defining and writing the Dockerfile with all requirements. After each step, update this board and provide feedback or request assistance as needed.