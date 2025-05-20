import os
import anthropic
import re
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import httpx
import threading
import logging
from datetime import datetime

CLAUDE_MODEL = "claude-3-5-sonnet-20240620"

logger = logging.getLogger("gmaildigest.summarization")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)

class AnthropicRateLimitError(Exception):
    pass


def summarize_email(text: str, api_key: str = None, max_retries: int = 2, timeout: int = 10) -> (str, bool):
    """
    Summarize the given email text using Claude 3.5 Sonnet if API key is provided,
    otherwise use local extractive summarization (sumy).
    Returns (summary, used_fallback: bool).
    """
    prompt = (
        "Summarize the following email in 500 characters or less. "
        "Prioritize conciseness, key points, action items, and deadlines. "
        "Omit greetings, signatures, and boilerplate.\n\n"
        f"{text}"
    )
    if api_key:
        try:
            client = anthropic.Anthropic(api_key=api_key)
            for attempt in range(max_retries):
                result = {}
                def call_anthropic():
                    try:
                        response = client.messages.create(
                            model=CLAUDE_MODEL,
                            max_tokens=512,
                            temperature=0.2,
                            system="You are a helpful assistant that summarizes emails.",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        result['response'] = response
                    except Exception as e:
                        result['error'] = e
                thread = threading.Thread(target=call_anthropic)
                thread.start()
                thread.join(timeout)
                if thread.is_alive():
                    # Timeout occurred
                    thread.join(0)
                    logger.warning(f"Anthropic API call timed out at {datetime.now()}")
                    raise AnthropicRateLimitError("Anthropic API call timed out")
                if 'error' in result:
                    err_str = str(result['error'])
                    if '429' in err_str or 'Too Many Requests' in err_str or '529' in err_str:
                        logger.warning(f"Anthropic API rate limit ({err_str}) at {datetime.now()}")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(2 ** attempt)
                            continue
                        else:
                            raise AnthropicRateLimitError("Anthropic API rate limit (HTTP 429/529)")
                    logger.error(f"Anthropic API error: {err_str} at {datetime.now()}")
                    raise result['error']
                response = result.get('response')
                # Check for rate limit in response content (paranoid check)
                if hasattr(response, 'status_code') and response.status_code in (429, 529):
                    logger.warning(f"Anthropic API rate limit (status_code {response.status_code}) at {datetime.now()}")
                    raise AnthropicRateLimitError(f"Anthropic API rate limit ({response.status_code})")
                if hasattr(response, 'content') and hasattr(response.content[0], 'text'):
                    text_content = response.content[0].text.strip()
                    if 'Too Many Requests' in text_content or 'rate limit' in text_content:
                        logger.warning(f"Anthropic API rate limit (content) at {datetime.now()}")
                        raise AnthropicRateLimitError("Anthropic API rate limit (content)")
                    return text_content, False
                # Fallback: if response is not as expected
                logger.error(f"Anthropic API returned unexpected response at {datetime.now()}")
                raise AnthropicRateLimitError("Anthropic API returned unexpected response")
        except AnthropicRateLimitError as e:
            logger.info(f"Falling back to local summarizer due to rate limit: {e} at {datetime.now()}")
        except Exception as e:
            logger.error(f"Anthropic API exception: {e} at {datetime.now()}")
    # Local summarizer
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, 3)
        summary = " ".join(str(sentence) for sentence in summary_sentences)
        return summary.strip(), True
    except Exception as e:
        logger.error(f"Local summarizer failed: {e} at {datetime.now()}")
        return text[:500], True


def robust_summarize(subject, body, anthropic_api_key=None, char_limit=500):
    """
    Tiered summarization: Anthropic API -> local summarizer -> heuristic fallback.
    Returns (summary, method_used)
    """
    # 1. Try Anthropic API
    if anthropic_api_key:
        try:
            prompt = (
                f"Summarize this email in a single concise paragraph of less than {char_limit} characters, "
                f"focusing only on the essential information without adding commentary:\n{subject}\n{body}"
            )
            summary, used_fallback = summarize_email(prompt, anthropic_api_key)
            if summary and not summary.lower().startswith("summarize this email"):
                return summary, "local" if used_fallback else "anthropic"
        except AnthropicRateLimitError as e:
            logger.info(f"Anthropic API rate limit in robust_summarize: {e} at {datetime.now()}")
        except Exception as e:
            logger.error(f"Anthropic API exception in robust_summarize: {e} at {datetime.now()}")
    # 2. Try local summarizer
    try:
        summary, _ = summarize_email(f"{subject}\n{body}")
        if summary:
            return summary, "local"
    except Exception as e:
        logger.error(f"Local summarizer failed in robust_summarize: {e} at {datetime.now()}")
    # 3. Heuristic fallback
    try:
        sentences = body.split('. ')
        fallback = '. '.join(sentences[:3])
        if len(fallback) > char_limit:
            fallback = fallback[:char_limit-3] + '...'
        return fallback or subject, "fallback"
    except Exception as e:
        logger.error(f"Heuristic fallback failed in robust_summarize: {e} at {datetime.now()}")
        return subject, "fallback"


def estimate_reading_time(text: str) -> float:
    """
    Estimate reading time in minutes for the given text.
    Uses 225 words per minute as the base speed.
    """
    word_count = len(re.findall(r'\w+', text))
    minutes = word_count / 225
    # Round to nearest half minute
    return round(minutes * 2) / 2 