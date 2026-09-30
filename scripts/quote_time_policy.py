"""Shared timestamp policy for authenticated public market quotes.

Robinhood quote timestamps are authoritative source timestamps. A small,
bounded tolerance handles clock skew between the broker response and the
scanner host without rewriting the original timestamp or treating an old
quote as fresh.
"""

MAX_FUTURE_QUOTE_SKEW_SECONDS = 30.0


def quote_age_is_fresh(age_seconds, max_age_seconds):
    """Return whether a quote age is within the stale and clock-skew bounds."""
    return (
        isinstance(age_seconds, (int, float))
        and isinstance(max_age_seconds, (int, float))
        and -MAX_FUTURE_QUOTE_SKEW_SECONDS <= age_seconds <= max_age_seconds
    )
