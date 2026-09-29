"""Golden tests for the deterministic address normalizer."""

from __future__ import annotations

import json
from pathlib import Path

from addressiq.normalize.normalizer import normalize_address

_GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "normalizer_cases.json"


def test_normalizer_golden_cases() -> None:
    """Each saved input maps to the saved normalized text, tokens, and pincode."""
    cases = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert isinstance(cases, list)
    for case in cases:
        result = normalize_address(case["input"])
        assert result.text == case["text"]
        assert result.tokens == case["tokens"]
        assert result.pincode == case["pincode"]
        assert result.raw == case["input"]


def test_normalizer_is_idempotent() -> None:
    """Running the normalizer on its own output does not change the text."""
    cases = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    for case in cases:
        once = normalize_address(case["input"])
        twice = normalize_address(once.text)
        assert twice.text == once.text
        assert twice.pincode == once.pincode
