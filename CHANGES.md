# Gmail Digest Assistant - Changelog

## [Unreleased]
- Urgency display now uses emojis: 🟢 Normal, 🔴 Urgent, ⭐ Important.
- Digest summary logic improved: Claude-style prompt, no subject/body labels, concise paragraph only.
- Subject is truncated to 200 characters if needed.
- Summaries strip links, images, and non-textual content.
- Digest formatting and inline button features iteratively improved for clarity and usability.
- **Robust summarization failover:** Now uses Anthropic API first, then local summarizer, then heuristic fallback. Digest indicates if a local or fallback summary was used.

## Earlier Iterations
- See project commit history for previous changes. 