"""Label folding and India Post office-name cleanup."""

from __future__ import annotations

import re
import unicodedata

from addressiq.normalize.normalizer import normalize_address

_OFFICE_SUFFIX = re.compile(
    r"\s+(?:g\.?\s*p\.?\s*o|s\.?\s*o|b\.?\s*o|h\.?\s*o)\.?\s*$",
    re.IGNORECASE,
)
_CANONICAL_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("palli", "pally"),
    ("peta", "pet"),
    ("ganj", "gunj"),
)


def fold_label(value: str) -> str:
    """Casefold a place label and keep only alphanumeric characters."""
    folded = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in folded if char.isalnum())


def strip_office_suffix(office_name: str) -> str:
    """Remove a trailing India Post office type such as S.O, B.O, or G.P.O."""
    return _OFFICE_SUFFIX.sub("", office_name).strip()


def title_name(value: str) -> str:
    """Title-case a cleaned locality name."""
    return " ".join(part.capitalize() for part in value.split())


def canonical_key(name: str) -> str:
    """Normalize a locality name and collapse known spelling suffixes."""
    text = normalize_address(name).text
    return _apply_suffix(text, _CANONICAL_SUFFIXES)


def _apply_suffix(text: str, pairs: tuple[tuple[str, str], ...]) -> str:
    ordered = sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)
    for source, target in ordered:
        if text.endswith(source):
            return text[: -len(source)] + target
    return text
