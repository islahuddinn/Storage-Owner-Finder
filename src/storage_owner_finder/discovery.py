from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from storage_owner_finder.models import DiscoveryRequest, FacilityInput, InputMode


STATE_CATALOG: dict[str, list[FacilityInput]] = {
    "VT": [
        FacilityInput(
            facility_name="Killington Road Storage",
            address="1700 Killington Rd",
            city="Killington",
            state="VT",
            county="Rutland",
        )
    ],
    "MI": [
        FacilityInput(
            facility_name="Charlevoix Mini Storage",
            address="Near Charlevoix Airport",
            city="Charlevoix",
            state="MI",
            county="Charlevoix",
        )
    ],
    "NY": [
        FacilityInput(
            facility_name="Canandaigua Self Storage",
            address="6000-6025 Denny Dr",
            city="Canandaigua",
            state="NY",
            county="Ontario",
        )
    ],
    "CO": [
        FacilityInput(
            facility_name="All-Purpose Storage",
            address="Pagosa Springs",
            city="Pagosa Springs",
            state="CO",
            county="Archuleta",
        )
    ],
}


@dataclass(slots=True)
class FacilityDiscoveryService:
    def discover(self, request: DiscoveryRequest) -> list[FacilityInput]:
        if request.mode == InputMode.ADDRESS_LIST:
            return self._from_addresses(request.addresses)
        if request.mode == InputMode.CITY_STATE_BATCH:
            return self._from_city_state(request.city_state_pairs)
        if request.mode == InputMode.STATE_BATCH:
            return self._from_states(request.states)
        raise ValueError(f"Unsupported mode: {request.mode}")

    def _from_addresses(self, addresses: Iterable[dict]) -> list[FacilityInput]:
        rows: list[FacilityInput] = []
        for row in addresses:
            rows.append(
                FacilityInput(
                    facility_name=row.get("facility_name", ""),
                    address=row["address"],
                    city=row["city"],
                    state=row["state"].upper(),
                    county=row.get("county", ""),
                )
            )
        return rows

    def _from_city_state(self, city_state_pairs: Iterable[dict]) -> list[FacilityInput]:
        discovered: list[FacilityInput] = []
        for pair in city_state_pairs:
            city = pair["city"].strip().lower()
            state = pair["state"].strip().upper()
            for facility in STATE_CATALOG.get(state, []):
                if facility.city.lower() == city:
                    discovered.append(facility)
        return discovered

    def _from_states(self, states: Iterable[str]) -> list[FacilityInput]:
        discovered: list[FacilityInput] = []
        for state in states:
            discovered.extend(STATE_CATALOG.get(state.upper(), []))
        return discovered

