"""Formatting helpers for dashboard UI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "EUR",
    "GBP": "GBP",
    "NGN": "NGN",
    "CAD": "CAD",
    "AUD": "AUD",
    "INR": "INR",
}


def ago(value: Any) -> str:
    """Return a human-friendly relative time string."""
    if not isinstance(value, datetime):
        return ""
    dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    delta = now - dt

    if delta.days == 0:
        hours = delta.seconds // 3600
        if hours == 0:
            minutes = max(delta.seconds // 60, 1)
            return f"{minutes}m ago"
        return f"{hours}h ago"
    if delta.days == 1:
        return "1d ago"
    if delta.days < 30:
        return f"{delta.days}d ago"
    if delta.days < 365:
        return f"{delta.days // 30}mo ago"
    return f"{delta.days // 365}y ago"


def format_compensation(
    min_comp: int | None,
    max_comp: int | None,
    currency: str | None,
    period: str | None,
) -> str | None:
    """Format compensation fields into a compact badge string."""
    if min_comp is None and max_comp is None:
        return None

    currency_code = (currency or "").upper()
    prefix = _CURRENCY_SYMBOLS.get(currency_code, currency_code)
    suffix = f"/{period}" if period else ""

    if min_comp is not None and max_comp is not None:
        return f"{prefix}{min_comp:,}-{prefix}{max_comp:,} {currency_code}{suffix}".strip()
    if min_comp is not None:
        return f"{prefix}{min_comp:,}+ {currency_code}{suffix}".strip()
    return f"{prefix}{max_comp:,} {currency_code}{suffix}".strip()
