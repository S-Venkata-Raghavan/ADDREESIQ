"""Abbreviation expansions and noise tokens for address normalization."""

from __future__ import annotations

import re

# Longer phrases first. Trailing periods are left for the punctuation pass so
# "Rd.No.1" becomes "road no 1" instead of "roadno 1".
ABBREVIATION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bhouse\s+number\b", re.IGNORECASE), "house no"),
    (re.compile(r"\bh\s*\.?\s*no\b", re.IGNORECASE), "house no"),
    (re.compile(r"\bhouse\s+no\b", re.IGNORECASE), "house no"),
    (re.compile(r"\bdoor\s+number\b", re.IGNORECASE), "door no"),
    (re.compile(r"\bd\s*\.?\s*no\b", re.IGNORECASE), "door no"),
    (re.compile(r"\bdoor\s+no\b", re.IGNORECASE), "door no"),
    (re.compile(r"\bflat\s+number\b", re.IGNORECASE), "flat no"),
    (re.compile(r"\bf\s*\.?\s*no\b", re.IGNORECASE), "flat no"),
    (re.compile(r"\bflat\s+no\b", re.IGNORECASE), "flat no"),
    (re.compile(r"\bbldg\b", re.IGNORECASE), "building"),
    (re.compile(r"\bapt\b", re.IGNORECASE), "apartment"),
    (re.compile(r"\bflr\b", re.IGNORECASE), "floor"),
    (re.compile(r"\bqtrs\b", re.IGNORECASE), "quarters"),
    (re.compile(r"\bqtr\b", re.IGNORECASE), "quarter"),
    (re.compile(r"\bstn\b", re.IGNORECASE), "station"),
    (re.compile(r"\bopp\b", re.IGNORECASE), "opposite"),
    (re.compile(r"\bnr\b", re.IGNORECASE), "near"),
    (re.compile(r"\brd\b", re.IGNORECASE), "road"),
    (re.compile(r"\bst\b", re.IGNORECASE), "street"),
    (re.compile(r"\bcol\b", re.IGNORECASE), "colony"),
    (re.compile(r"\bph\b", re.IGNORECASE), "phase"),
)

NOISE_TOKENS: frozenset[str] = frozenset(
    {
        "hai",
        "ji",
        "ka",
        "ke",
        "ki",
        "kindly",
        "me",
        "mein",
        "paas",
        "par",
        "pe",
        "please",
        "the",
        "wahan",
        "wala",
        "wale",
        "wali",
        "ye",
    }
)


def expand_abbreviations(text: str) -> str:
    """Replace address abbreviations with their canonical words."""
    expanded = text
    for pattern, replacement in ABBREVIATION_PATTERNS:
        expanded = pattern.sub(replacement, expanded)
    return expanded
