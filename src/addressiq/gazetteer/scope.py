"""City scopes for gazetteer builds.

Hyderabad suburbs such as Kukatpally and Madhapur sit in Medchal-Malkajgiri
and Ranga Reddy, outside Hyderabad district. Those districts stay in scope.
"""

from __future__ import annotations

from addressiq.gazetteer.models import CityScope

HYDERABAD_SCOPE = CityScope(
    city="Hyderabad",
    state="Telangana",
    districts=("Hyderabad", "Ranga Reddy", "Medchal", "Medchal-Malkajgiri"),
)
