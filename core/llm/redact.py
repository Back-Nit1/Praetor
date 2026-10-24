"""Tokenize identifiers before text leaves the machine. Regex-only: names are NOT detected."""
from __future__ import annotations

import re

_STREET = (
    r"(?i:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|court|ct|way|place|pl|terrace|circle|highway|hwy)"
)
# Kinds in priority order: at one start position the first alternative that matches wins.
_PATTERNS = {
    "EMAIL": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",
    "ID": r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)|(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)",  # SSN-shaped, card-shaped
    "PHONE": r"(?<![\w+])(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)",
    # "100 Example Street", "42 5th Ave Apt 3": number + capitalised words + street suffix + optional unit
    "ADDRESS": rf"\b\d{{1,6}}\s+(?:(?:[A-Z][\w.'-]*|\d+(?:st|nd|rd|th))\s+){{1,4}}{_STREET}\b\.?"
    r"(?:,?\s*(?i:apt|unit|suite|ste)\.?\s*#?\w+|,?\s*#\w+)?",
    # long digit runs, or 8+ char tokens mixing letters and digits (keys, license/passport-style ids)
    "ID2": r"\b\d{9,}\b|\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{8,}\b",
}
_RX = re.compile("|".join(f"(?P<{k}>{v})" for k, v in _PATTERNS.items()))
_PLACEHOLDER = re.compile(r"<[A-Z]+_\d+>")


def redact(text: str, mapping: dict[str, str] | None = None) -> tuple[str, dict[str, str]]:
    """Return (text with <KIND_n> placeholders, placeholder->original map).

    Pass the same `mapping` across several strings (e.g. chat messages) to keep placeholders stable.
    """
    mapping = {} if mapping is None else mapping
    seen = {v: k for k, v in mapping.items()}

    def sub(m: re.Match) -> str:
        value, kind = m.group(), m.lastgroup.rstrip("2")
        if value not in seen:
            seen[value] = f"<{kind}_{sum(k.startswith(f'<{kind}_') for k in mapping) + 1}>"
            mapping[seen[value]] = value
        return seen[value]

    return _RX.sub(sub, text), mapping


def rehydrate(text: str, mapping: dict[str, str]) -> str:
    """Single pass, so restored values are never re-scanned."""
    return _PLACEHOLDER.sub(lambda m: mapping.get(m.group(), m.group()), text)
