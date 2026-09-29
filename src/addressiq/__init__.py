"""AddressIQ: normalize addresses and build a locality gazetteer."""

from addressiq.gazetteer.build import build_hyderabad_gazetteer
from addressiq.normalize.normalizer import normalize_address

__all__ = ["build_hyderabad_gazetteer", "normalize_address"]
