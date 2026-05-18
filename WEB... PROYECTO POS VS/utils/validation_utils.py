"""Utility helpers for validating and normalizing contact data."""

from __future__ import annotations

import re
from typing import Optional

_EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


def is_valid_email(value: Optional[str]) -> bool:
    """Return True when *value* looks like a valid email address."""
    if not value:
        return False
    candidate = value.strip()
    if not candidate:
        return False
    return bool(_EMAIL_REGEX.fullmatch(candidate))


def normalize_phone_number(value: Optional[str]) -> str:
    """Extract digits from *value* and drop leading local prefixes such as 00."""
    digits = "".join(filter(str.isdigit, value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


def ensure_country_prefix(digits: str, default_code: str = "51") -> str:
    """Ensure the phone number includes the *default_code* country prefix."""
    if not digits:
        return ""
    if digits.startswith(default_code):
        return digits
    if len(digits) == 9:  # local mobile without prefix
        return f"{default_code}{digits}"
    return digits


def format_phone_display(digits: str) -> str:
    """Return a phone number formatted for display (e.g. +51 999 888 777)."""
    if not digits:
        return ""
    cleaned = digits.strip()
    if cleaned.startswith("51") and len(cleaned) >= 11:
        local = cleaned[2:]
        if len(local) == 9:
            return f"+51 {local[:3]} {local[3:6]} {local[6:]}"
    return cleaned
