"""Records that cross the gazetteer boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from addressiq.normalize.normalizer import PINCODE_PATTERN


class PostOffice(BaseModel):
    """One India Post office, already loaded from a local file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    office_name: str
    pincode: str = Field(pattern=PINCODE_PATTERN)
    district: str
    state: str
    latitude: float | None = None
    longitude: float | None = None


class OsmPlace(BaseModel):
    """One OpenStreetMap place or suburb, already loaded from a local file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    alt_names: list[str] = Field(default_factory=list)
    city: str
    district: str | None = None
    state: str | None = None
    postcode: str | None = Field(default=None, pattern=PINCODE_PATTERN)
    latitude: float | None = None
    longitude: float | None = None


class CityScope(BaseModel):
    """Which state, city, and districts a gazetteer build includes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    city: str
    state: str
    districts: tuple[str, ...]


class Locality(BaseModel):
    """One gazetteer row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    locality_id: str
    name: str
    aliases: list[str]
    city: str
    district: str | None
    state: str
    pincodes: list[str]
    lat: float | None
    lon: float | None
