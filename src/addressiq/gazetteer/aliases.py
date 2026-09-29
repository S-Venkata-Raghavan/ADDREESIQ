"""Transliteration aliases for locality names.

Vowel-drop typos such as Hyderabad -> Hydrabad are synthetic noise (spec
section 6), not aliases, unless a source lists them explicitly.
"""

from __future__ import annotations

from collections.abc import Sequence

from addressiq.normalize.normalizer import normalize_address

_SUFFIX_VARIANTS: tuple[tuple[str, str], ...] = (
    ("pally", "palli"),
    ("palli", "pally"),
    ("puram", "pur"),
    ("peta", "pet"),
    ("pet", "peta"),
    ("gunj", "ganj"),
    ("ganj", "gunj"),
)
_INTERNAL_SWAPS: tuple[tuple[str, str], ...] = (
    ("aa", "a"),
    ("ee", "i"),
    ("oo", "u"),
)


def transliteration_variants(name: str) -> list[str]:
    """Return the name plus one-step Indian-English spelling variants."""
    variants = {name, _swap_suffix(name)}
    for source, target in _INTERNAL_SWAPS:
        if source in name:
            variants.add(name.replace(source, target, 1))
    variants.discard("")
    return sorted(variants)


def collect_aliases(canonical: str, extra_names: Sequence[str]) -> list[str]:
    """Return sorted aliases from the canonical name and source strings."""
    names = set(transliteration_variants(canonical))
    for extra in extra_names:
        normalized = normalize_address(extra).text
        if normalized:
            names.update(transliteration_variants(normalized))
    return sorted(names)


def _swap_suffix(name: str) -> str:
    ordered = sorted(_SUFFIX_VARIANTS, key=lambda pair: len(pair[0]), reverse=True)
    for source, target in ordered:
        if name.endswith(source):
            return name[: -len(source)] + target
    return name
