from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from storage_owner_finder.models import DiscoveryRequest, FacilityInput, InputMode
from storage_owner_finder.osm_discovery import OSMStorageDiscovery


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
            return self._from_city_state(request)
        if request.mode == InputMode.STATE_BATCH:
            return self._from_states(request)
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

    def _from_city_state(self, request: DiscoveryRequest) -> list[FacilityInput]:
        discovered: list[FacilityInput] = []
        osm = OSMStorageDiscovery()
        for pair in request.city_state_pairs:
            city = pair["city"].strip()
            state = pair["state"].strip().upper()
            radius = int(pair.get("radius_m", request.radius_meters))
            max_f = int(pair.get("max_facilities", request.max_facilities))
            found: list[FacilityInput] = []
            if request.use_osm_discovery:
                found = osm.discover_near_city(
                    city, state, radius_m=radius, max_facilities=max_f
                )
            if not found:
                for facility in STATE_CATALOG.get(state, []):
                    if facility.city.lower() == city.lower():
                        found.append(facility)
            discovered.extend(found)
        return discovered

    def _from_states(self, request: DiscoveryRequest) -> list[FacilityInput]:
        discovered: list[FacilityInput] = []
        osm = OSMStorageDiscovery()
        per_state_cap = max(50, request.max_facilities)
        for state in request.states:
            st = state.strip().upper()
            found: list[FacilityInput] = []
            if request.use_osm_discovery:
                found = osm.discover_in_state_bbox(
                    st, max_facilities=per_state_cap
                )
            if not found:
                found = list(STATE_CATALOG.get(st, []))
            discovered.extend(found)
        return discovered
