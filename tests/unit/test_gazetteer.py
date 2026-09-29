"""Golden and table-driven tests for the Hyderabad gazetteer builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from addressiq.gazetteer.build import build_hyderabad_gazetteer
from addressiq.gazetteer.models import OsmPlace, PostOffice
from addressiq.gazetteer.text import canonical_key, strip_office_suffix

_ROOT = Path(__file__).resolve().parents[1]
_OFFICES = _ROOT / "fixtures" / "hyderabad_post_offices.json"
_PLACES = _ROOT / "fixtures" / "hyderabad_osm_places.json"
_GOLDEN = _ROOT / "golden" / "hyderabad_gazetteer.json"


def test_hyderabad_gazetteer_matches_golden() -> None:
    """India Post and OSM fixtures merge into the saved Hyderabad gazetteer."""
    built = [
        locality.model_dump(mode="json")
        for locality in build_hyderabad_gazetteer(_offices(), _places())
    ]
    expected = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert built == expected


def test_gazetteer_build_ignores_input_order() -> None:
    """The same records in reverse order produce the same localities."""
    forward = build_hyderabad_gazetteer(_offices(), _places())
    backward = build_hyderabad_gazetteer(list(reversed(_offices())), list(reversed(_places())))
    assert forward == backward


@pytest.mark.parametrize(
    ("office_name", "expected"),
    [
        ("Kukatpally S.O", "Kukatpally"),
        ("Kukatpally SO", "Kukatpally"),
        ("Kukatpally S.O.", "Kukatpally"),
        ("Something B.O", "Something"),
        ("Hyderabad G.P.O", "Hyderabad"),
        ("Hyderabad GPO", "Hyderabad"),
    ],
)
def test_strip_office_suffix(office_name: str, expected: str) -> None:
    """Trailing India Post office types are removed from the locality name."""
    assert strip_office_suffix(office_name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Kukatpalli", "kukatpally"),
        ("Kukatpally", "kukatpally"),
        ("Nizampeta", "nizampet"),
        ("Nizampet", "nizampet"),
    ],
)
def test_canonical_key_collapses_spelling_suffixes(name: str, expected: str) -> None:
    """Palli/pally and peta/pet spellings share one gazetteer key."""
    assert canonical_key(name) == expected


def test_post_office_rejects_bad_pincode() -> None:
    """A pincode that is not six digits never enters the builder."""
    with pytest.raises(ValidationError):
        PostOffice(
            office_name="Abids S.O",
            pincode="5000",
            district="Hyderabad",
            state="Telangana",
        )


def _offices() -> list[PostOffice]:
    payload = json.loads(_OFFICES.read_text(encoding="utf-8"))
    return [PostOffice.model_validate(row) for row in payload]


def _places() -> list[OsmPlace]:
    payload = json.loads(_PLACES.read_text(encoding="utf-8"))
    return [OsmPlace.model_validate(row) for row in payload]
