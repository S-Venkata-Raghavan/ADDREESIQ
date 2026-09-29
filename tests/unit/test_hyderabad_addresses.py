"""Hand-written Hyderabad addresses checked against the normalizer.

Place names and pincodes come from all_india_pincode_directory_2025.csv.
Spellings such as Lunger House, Putlibowli, Jntu Kukat Pally, and Zamistanpur
are kept as published. Hyd, Hydrabad, Kukatpalli, and Sec-bad are not corrected.
"""

from __future__ import annotations

import json
from pathlib import Path

from addressiq.normalize.normalizer import normalize_address

_GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "hyderabad_messy_addresses.json"
_EXPECTED_COUNT = 45


def test_hyderabad_messy_addresses() -> None:
    """Each hand-written address matches its expected text and pincode."""
    cases = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert len(cases) == _EXPECTED_COUNT
    for case in cases:
        result = normalize_address(case["input"])
        assert result.text == case["text"], case["input"]
        assert result.tokens == case["text"].split()
        assert result.pincode == case["pincode"]
        assert result.raw == case["input"]


def test_hyderabad_messy_addresses_are_idempotent() -> None:
    """Normalizing the normalized text again does not change it."""
    cases = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    for case in cases:
        once = normalize_address(case["input"])
        twice = normalize_address(once.text)
        assert twice.text == once.text
        assert twice.pincode == once.pincode
