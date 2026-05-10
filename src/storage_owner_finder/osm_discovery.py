from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from storage_owner_finder.models import FacilityInput

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

DEFAULT_USER_AGENT = "StorageOwnerFinder/1.0 (MVP; contact via repo maintainer)"


@dataclass(slots=True)
class OSMStorageDiscovery:
    """Discover self-storage / storage-rental POIs via OpenStreetMap (Nominatim + Overpass)."""

    user_agent: str = DEFAULT_USER_AGENT
    timeout: float = 90.0

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        )

    def geocode_city_state(self, city: str, state: str) -> tuple[float, float]:
        q = f"{city}, {state}, United States"
        with self._client() as client:
            r = client.get(
                NOMINATIM_URL,
                params={"q": q, "format": "json", "limit": 1},
            )
            r.raise_for_status()
            data = r.json()
        if not data:
            raise ValueError(f"No geocode result for: {q}")
        return float(data[0]["lat"]), float(data[0]["lon"])

    def geocode_state(self, state: str) -> tuple[float, float, list[str]]:
        """Return center lat, lon and Nominatim boundingbox [south, north, west, east]."""
        q = f"{state}, United States"
        with self._client() as client:
            r = client.get(
                NOMINATIM_URL,
                params={"q": q, "format": "json", "limit": 1},
            )
            r.raise_for_status()
            data = r.json()
        if not data:
            raise ValueError(f"No geocode result for: {q}")
        row = data[0]
        bbox = row.get("boundingbox")
        if not bbox or len(bbox) != 4:
            raise ValueError(f"No bounding box for state: {state}")
        return float(row["lat"]), float(row["lon"]), bbox

    def _overpass_around(
        self, lat: float, lon: float, radius_m: int, max_results: int
    ) -> list[dict[str, Any]]:
        # Cap Overpass payload; split if needed in future.
        q = f"""
[out:json][timeout:90];
(
  node["shop"="storage_rental"](around:{radius_m},{lat},{lon});
  way["shop"="storage_rental"](around:{radius_m},{lat},{lon});
  node["amenity"="self_storage"](around:{radius_m},{lat},{lon});
  way["amenity"="self_storage"](around:{radius_m},{lat},{lon});
);
out center tags;
"""
        with self._client() as client:
            r = client.post(OVERPASS_URL, content=q.encode("utf-8"))
            r.raise_for_status()
            payload = r.json()
        elements = list(payload.get("elements", []))
        return elements[: max(max_results * 5, 500)]

    def _overpass_bbox(
        self,
        south: float,
        west: float,
        north: float,
        east: float,
        max_results: int,
    ) -> list[dict[str, Any]]:
        q = f"""
[out:json][timeout:90];
(
  node["shop"="storage_rental"]({south},{west},{north},{east});
  way["shop"="storage_rental"]({south},{west},{north},{east});
  node["amenity"="self_storage"]({south},{west},{north},{east});
  way["amenity"="self_storage"]({south},{west},{north},{east});
);
out center tags;
"""
        with self._client() as client:
            r = client.post(OVERPASS_URL, content=q.encode("utf-8"))
            r.raise_for_status()
            payload = r.json()
        elements = list(payload.get("elements", []))
        return elements[: max(max_results * 5, 500)]

    @staticmethod
    def _element_to_facility(
        el: dict[str, Any],
        fallback_city: str,
        fallback_state: str,
    ) -> FacilityInput | None:
        tags = el.get("tags") or {}
        name = (tags.get("name") or "").strip() or "Self storage (unnamed)"
        housenumber = (tags.get("addr:housenumber") or "").strip()
        street = (tags.get("addr:street") or "").strip()
        line1 = " ".join(p for p in (housenumber, street) if p).strip()
        city = (tags.get("addr:city") or "").strip() or fallback_city
        tag_state = (tags.get("addr:state") or "").strip().upper()
        fb = fallback_state.strip().upper()
        if len(fb) == 2:
            state_code = fb
        elif len(tag_state) == 2:
            state_code = tag_state
        else:
            state_code = tag_state[:2] if tag_state else fb[:2] if fb else "US"

        if "lat" in el and "lon" in el:
            lat, lon = float(el["lat"]), float(el["lon"])
        elif "center" in el:
            lat = float(el["center"]["lat"])
            lon = float(el["center"]["lon"])
        else:
            return None

        address = line1 or f"{lat:.5f},{lon:.5f}"
        return FacilityInput(
            facility_name=name,
            address=address,
            city=city,
            state=state_code,
            county="",
        )

    def discover_near_city(
        self,
        city: str,
        state: str,
        *,
        radius_m: int = 25_000,
        max_facilities: int = 200,
    ) -> list[FacilityInput]:
        try:
            lat, lon = self.geocode_city_state(city, state)
        except Exception as exc:
            logger.warning("OSM geocode failed for %s, %s: %s", city, state, exc)
            return []

        try:
            elements = self._overpass_around(lat, lon, radius_m, max_facilities)
        except Exception as exc:
            logger.warning("Overpass around failed: %s", exc)
            return []

        out: list[FacilityInput] = []
        seen: set[tuple[str, str, str]] = set()
        for el in elements:
            fac = self._element_to_facility(el, city, state)
            if fac is None:
                continue
            key = (fac.facility_name.lower(), fac.address.lower(), fac.city.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append(fac)
            if len(out) >= max_facilities:
                break
        return out

    def discover_in_state_bbox(
        self,
        state: str,
        *,
        max_facilities: int = 300,
    ) -> list[FacilityInput]:
        try:
            _lat, _lon, bbox = self.geocode_state(state)
            south, north, west, east = map(float, bbox)
        except Exception as exc:
            logger.warning("OSM state geocode failed for %s: %s", state, exc)
            return []

        try:
            elements = self._overpass_bbox(south, west, north, east, max_facilities)
        except Exception as exc:
            logger.warning("Overpass bbox failed: %s", exc)
            return []

        st = state.strip().upper()
        abbr = st if len(st) == 2 else st[:2]
        out: list[FacilityInput] = []
        seen: set[tuple[str, str, str]] = set()
        for el in elements:
            fac = self._element_to_facility(el, "", abbr)
            if fac is None:
                continue
            key = (fac.facility_name.lower(), fac.address.lower(), fac.city.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append(fac)
            if len(out) >= max_facilities:
                break
        return out
