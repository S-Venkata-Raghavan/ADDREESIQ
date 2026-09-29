"""Deterministic address normalizer.

Lowercases text, folds scripts and digits, expands abbreviations, and drops
Hinglish filler tokens. Spelling correction is left to the gazetteer.
"""

from __future__ import annotations

import re
import unicodedata

from addressiq.normalize.abbreviations import NOISE_TOKENS, expand_abbreviations
from addressiq.normalize.models import NormalizedAddress

PINCODE_LENGTH = 6
PINCODE_PATTERN = rf"^[1-9][0-9]{{{PINCODE_LENGTH - 1}}}$"
PINCODE_RE = re.compile(PINCODE_PATTERN)
_PINCODE_HYPHEN = re.compile(
    rf"(?<=\d{{{PINCODE_LENGTH}}})-(?=\d{{{PINCODE_LENGTH}}}\b)"
    rf"|(?<=\D)-(?=\d{{{PINCODE_LENGTH}}}\b)"
    rf"|(?<=\d{{{PINCODE_LENGTH}}})-(?=\D)"
)
_SEPARATORS = re.compile(r"[^\w\s/-]+", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")
_ZERO_WIDTH = frozenset("\u200b\u200c\u200d\ufeff")
_DIGIT_TRANSLATION = str.maketrans(
    "०१२३४५६७८९٠١٢٣٤٥६٧٨٩",
    "01234567890123456789",
)
_APOSTROPHE_DELETE = str.maketrans("", "", "'\u2018\u2019\u02bc")


def normalize_address(raw: str) -> NormalizedAddress:
    """Normalize one address. The same input always yields the same output."""
    folded = _fold_scripts(raw)
    separated = _split_pincode_hyphens(folded)
    expanded = expand_abbreviations(separated)
    cleaned = _collapse(expanded)
    tokens = [token for token in cleaned.split(" ") if token and token not in NOISE_TOKENS]
    text = " ".join(tokens)
    return NormalizedAddress(
        raw=raw,
        text=text,
        tokens=tokens,
        pincode=_single_pincode(tokens),
    )


def _fold_scripts(raw: str) -> str:
    """Apply NFKC, drop zero-width characters, and map Indic digits to ASCII."""
    normalized = unicodedata.normalize("NFKC", raw)
    without_zero_width = "".join(char for char in normalized if char not in _ZERO_WIDTH)
    folded = without_zero_width.translate(_DIGIT_TRANSLATION)
    return folded.translate(_APOSTROPHE_DELETE).casefold()


def _split_pincode_hyphens(text: str) -> str:
    """Split a hyphen that only exists to attach a 6-digit pincode."""
    return _PINCODE_HYPHEN.sub(" ", text)


def _collapse(text: str) -> str:
    """Turn punctuation into spaces and collapse repeated whitespace."""
    separated = _SEPARATORS.sub(" ", text)
    return _WHITESPACE.sub(" ", separated).strip()


def _single_pincode(tokens: list[str]) -> str | None:
    """Return the pincode only when the address contains exactly one."""
    found = [token for token in tokens if PINCODE_RE.fullmatch(token)]
    if len(found) == 1:
        return found[0]
    return None
