"""Normalized address returned by the normalizer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NormalizedAddress(BaseModel):
    """Deterministic normalization of one raw address string."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw: str
    text: str
    tokens: list[str]
    pincode: str | None = Field(
        default=None,
        description="The only 6-digit pincode in the text, or null when missing or ambiguous.",
    )
