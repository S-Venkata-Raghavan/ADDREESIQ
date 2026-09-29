"""Pure gazetteer builder. Callers pass already loaded records; this module does no IO."""

from __future__ import annotations

from collections.abc import Sequence

from addressiq.gazetteer.aliases import collect_aliases
from addressiq.gazetteer.models import CityScope, Locality, OsmPlace, PostOffice
from addressiq.gazetteer.scope import HYDERABAD_SCOPE
from addressiq.gazetteer.text import (
    canonical_key,
    fold_label,
    strip_office_suffix,
    title_name,
)

COORD_DECIMALS = 6


def build_hyderabad_gazetteer(
    offices: Sequence[PostOffice],
    places: Sequence[OsmPlace],
) -> list[Locality]:
    """Build one locality row per Hyderabad place from India Post and OSM inputs."""
    return build_gazetteer(offices, places, HYDERABAD_SCOPE)


def build_gazetteer(
    offices: Sequence[PostOffice],
    places: Sequence[OsmPlace],
    scope: CityScope,
) -> list[Locality]:
    """Merge post offices and OSM places that fall inside ``scope``."""
    city_key = canonical_key(scope.city)
    grouped_offices = _group_offices(offices, scope, city_key)
    grouped_places = _group_places(places, scope, city_key)
    keys = sorted(set(grouped_offices) | set(grouped_places))
    return _assemble_all(keys, grouped_offices, grouped_places, scope)


def _assemble_all(
    keys: list[str],
    grouped_offices: dict[str, list[PostOffice]],
    grouped_places: dict[str, list[OsmPlace]],
    scope: CityScope,
) -> list[Locality]:
    localities: list[Locality] = []
    for key in keys:
        locality = _assemble(
            key,
            grouped_offices.get(key, []),
            grouped_places.get(key, []),
            scope,
        )
        if locality is not None:
            localities.append(locality)
    return localities


def _group_offices(
    offices: Sequence[PostOffice],
    scope: CityScope,
    city_key: str,
) -> dict[str, list[PostOffice]]:
    grouped: dict[str, list[PostOffice]] = {}
    district_keys = _district_keys(scope)
    for office in offices:
        key = _office_key(office, scope, district_keys, city_key)
        if key is None:
            continue
        grouped.setdefault(key, []).append(office)
    return grouped


def _group_places(
    places: Sequence[OsmPlace],
    scope: CityScope,
    city_key: str,
) -> dict[str, list[OsmPlace]]:
    grouped: dict[str, list[OsmPlace]] = {}
    district_keys = _district_keys(scope)
    for place in places:
        key = _place_key(place, scope, district_keys, city_key)
        if key is None:
            continue
        grouped.setdefault(key, []).append(place)
    return grouped


def _office_key(
    office: PostOffice,
    scope: CityScope,
    district_keys: frozenset[str],
    city_key: str,
) -> str | None:
    if not _office_in_scope(office, scope, district_keys):
        return None
    key = canonical_key(strip_office_suffix(office.office_name))
    if not key or key == city_key:
        return None
    return key


def _place_key(
    place: OsmPlace,
    scope: CityScope,
    district_keys: frozenset[str],
    city_key: str,
) -> str | None:
    if not _place_in_scope(place, scope, district_keys):
        return None
    key = canonical_key(place.name)
    if not key or key == city_key:
        return None
    return key


def _assemble(
    key: str,
    offices: list[PostOffice],
    places: list[OsmPlace],
    scope: CityScope,
) -> Locality | None:
    if not offices and not places:
        return None
    lat, lon = _coordinates(offices, places)
    slug = key.replace(" ", "-")
    return Locality(
        locality_id=f"{fold_label(scope.city)}:{slug}",
        name=_display_name(key, offices, places),
        aliases=collect_aliases(key, _alias_sources(offices, places)),
        city=scope.city,
        district=_district(offices, places),
        state=scope.state,
        pincodes=_pincodes(offices, places),
        lat=lat,
        lon=lon,
    )


def _office_in_scope(
    office: PostOffice,
    scope: CityScope,
    district_keys: frozenset[str],
) -> bool:
    same_state = fold_label(office.state) == fold_label(scope.state)
    return same_state and fold_label(office.district) in district_keys


def _place_in_scope(
    place: OsmPlace,
    scope: CityScope,
    district_keys: frozenset[str],
) -> bool:
    same_state = place.state is None or fold_label(place.state) == fold_label(scope.state)
    if not same_state:
        return False
    if fold_label(place.city) == fold_label(scope.city):
        return True
    if place.district is None:
        return False
    return fold_label(place.district) in district_keys


def _district_keys(scope: CityScope) -> frozenset[str]:
    return frozenset(fold_label(district) for district in scope.districts)


def _display_name(key: str, offices: Sequence[PostOffice], places: Sequence[OsmPlace]) -> str:
    if places:
        return sorted(places, key=lambda place: place.name)[0].name
    if offices:
        first = sorted(offices, key=lambda office: office.office_name)[0]
        return title_name(strip_office_suffix(first.office_name))
    return title_name(key)


def _alias_sources(offices: Sequence[PostOffice], places: Sequence[OsmPlace]) -> list[str]:
    names = [strip_office_suffix(office.office_name) for office in offices]
    for place in places:
        names.append(place.name)
        names.extend(place.alt_names)
    return names


def _district(offices: Sequence[PostOffice], places: Sequence[OsmPlace]) -> str | None:
    for place in sorted(places, key=lambda item: item.name):
        if place.district:
            return place.district
    for office in sorted(offices, key=lambda item: item.office_name):
        if office.district:
            return office.district
    return None


def _pincodes(offices: Sequence[PostOffice], places: Sequence[OsmPlace]) -> list[str]:
    found = {office.pincode for office in offices}
    for place in places:
        if place.postcode:
            found.add(place.postcode)
    return sorted(found)


def _coordinates(
    offices: Sequence[PostOffice],
    places: Sequence[OsmPlace],
) -> tuple[float | None, float | None]:
    for place in sorted(places, key=lambda item: item.name):
        pair = _round_pair(place.latitude, place.longitude)
        if pair is not None:
            return pair
    for office in sorted(offices, key=lambda item: item.office_name):
        pair = _round_pair(office.latitude, office.longitude)
        if pair is not None:
            return pair
    return None, None


def _round_pair(lat: float | None, lon: float | None) -> tuple[float, float] | None:
    if lat is None or lon is None:
        return None
    return (round(lat, COORD_DECIMALS), round(lon, COORD_DECIMALS))
