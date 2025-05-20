# Gmail Digest Assistant - Test Plan

## Test Environment Setup

### Prerequisites
- Python 3.8+ with venv
- Test Gmail account with sample emails
- Test Telegram bot token
- Clean system environment (no conflicting environment variables)

### Setup Steps
1. Create a fresh virtual environment
   ```bash
   python -m venv test_venv
   source test_venv/bin/activate  # On Windows: test_venv\Scripts\activate
   ```

2. Install dependencies
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-mock pytest-cov
   ```

3. Configure test environment
   ```bash
   # Create test .env file with test credentials
   python setup_config.py
   ```

4. Prepare test data
   - Set up Gmail test account with controlled set of emails
   - Create Telegram test bot via BotFather

## Test Categories

### 1. Unit Tests
Testing individual components in isolation.

#### Gmail Service Tests
- Authentication flow
- Email fetching
- Email parsing
- Search functionality
- Email forwarding
- Sender importance marking

#### Telegram Bot Tests
- Command parsing
- Message formatting
- Digest generation
- Notification handling
- Button callback processing
- Deadline detection algorithm

#### Configuration Tests
- Environment variable loading
- .env file parsing (plain and encrypted)
- Setup GUI validation

### 2. Integration Tests
Testing components working together.

#### Gmail API + Telegram Bot
- End-to-end email fetching and notification
- Digest generation from real email data
- Command execution affecting Gmail operations

#### Configuration + Main Application
- Environment variable propagation
- Encrypted configuration handling
- Credentials management

### 3. System Tests
Testing the entire application.

#### Full Workflow Tests
- Application startup to shutdown
- Authentication flow
- Command execution
- Scheduled operations
- Error handling and recovery

### 4. Performance Tests
- Response time for digest generation
- Memory usage during extended operation
- Bot responsiveness under load
- API rate limit handling

### 5. Security Tests
- Credential storage security
- .env encryption/decryption
- Token handling
- Permission validation

## Specific Test Cases

### Functional Tests

| ID | Component | Test Case | Expected Result | Priority |
|----|-----------|-----------|----------------|----------|
| F1 | Auth | OAuth2 authentication flow | Successful token acquisition | High |
| F2 | Auth | Token refresh mechanism | Token refreshed when expired | High |
| F3 | Gmail | Fetch emails from inbox | Correct emails retrieved | High |
| F4 | Gmail | Search emails by query | Matching emails returned | Medium |
| F5 | Gmail | Mark sender as important | Sender added to important list | Medium |
| F6 | Gmail | Forward email | Email forwarded to designated address | Medium |
| F7 | Telegram | /start command | Welcome message + job scheduling | High |
| F8 | Telegram | /digest command | Correctly formatted digest returned | High |
| F9 | Telegram | /set_interval command | Interval updated + job rescheduled | Medium |
| F10 | Telegram | /settings command | Settings displayed correctly | Low |
| F11 | Telegram | Button interface | Callbacks processed correctly | Medium |
| F12 | Telegram | Real-time notifications | Important emails trigger notifications | High |
| F13 | Config | GUI setup tool | .env file created correctly | High |
| F14 | Config | Encrypted .env handling | Successful encryption and decryption | Medium |

### Edge Case Tests

| ID | Category | Test Case | Expected Result | Priority |
|----|----------|-----------|----------------|----------|
| E1 | Concurrency | Multiple commands simultaneously | All commands processed correctly | Medium |
| E2 | i18n | Non-Latin characters in emails | Correctly processed and displayed | Low |
| E3 | Durability | 24+ hour continuous operation | Stable operation, no memory leaks | High |
| E4 | Storage | Large emails/attachments | Graceful handling without crashes | Medium |
| E5 | Recovery | Force application crash | Proper cleanup and recovery on restart | High |
| E6 | Network | Intermittent connectivity | Graceful error handling and retry | High |
| E7 | API | Gmail API rate limiting | Backoff and retry mechanism works | Medium |

### Security Tests

| ID | Category | Test Case | Expected Result | Priority |
|----|----------|-----------|----------------|----------|
| S1 | Encryption | .env password validation | Rejects incorrect passwords | High |
| S2 | Storage | Token file permissions | Restricted to current user only | High |
| S3 | Input | Command injection attempts | Safely handled, no execution | High |
| S4 | Privacy | Email data handling | No unnecessary data storage | Medium |

## Test Matrix

We'll track test execution and results in a separate test matrix document.

## Test Report Format

The final test report will include:

1. **Executive Summary**
   - Overall pass/fail metrics
   - Key findings
   - Recommendations

2. **Detailed Results**
   - Test case results with evidence
   - Bugs/issues discovered
   - Performance metrics

3. **Issue Log**
   - Critical issues
   - Non-critical issues and limitations
   - Proposed fixes

4. **Security Assessment**
   - Encryption effectiveness
   - Vulnerability scan results
   - Recommended security improvements

5. **Recommendations**
   - Code quality improvements
   - Architecture enhancements
   - Maintenance considerations

## Testing Timeline

1. Day 1: Environment setup and unit tests
2. Day 2: Integration tests and system tests
3. Day 3: Edge cases, security tests, and performance tests
4. Day 4: Report generation and issue fixing 