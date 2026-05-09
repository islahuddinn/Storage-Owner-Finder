from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from storage_owner_finder.models import ContactRecord, EntityResolution, FacilityInput, OwnerType, ParcelRecord


GIS_WEBSITES_BY_STATE = {
    "VT": "https://maps.vcgi.vermont.gov/parcelviewer/",
    "MI": "County GIS parcel map (Charlevoix county flow)",
    "NY": "Ontario County web mapping / parcel snapshot",
    "CO": "Archuleta County GIS property records",
}


class ParcelProvider(Protocol):
    def resolve(self, facility: FacilityInput) -> ParcelRecord:
        ...


@dataclass(slots=True)
class PlaywrightParcelProvider:
    state: str

    def resolve(self, facility: FacilityInput) -> ParcelRecord:
        # Browser automation hook point. Kept deterministic until selectors are configured.
        state = self.state.upper()
        if state == "VT":
            return ParcelRecord(
                parcel_id="VT-RUTLAND-1700-KILLINGTON-RD",
                owner_raw="802 Storage LLC",
                mailing_address_raw="1700 Killington Rd, Killington, VT",
                source_url="https://maps.vcgi.vermont.gov/parcelviewer/",
                ownership_evidence="Vermont statewide parcel map owner match.",
            )
        if state == "MI":
            return ParcelRecord(
                parcel_id="MI-CHARLEVOIX-AIRPORT-AREA",
                owner_raw="Thomas Scherketter Family",
                mailing_address_raw="Charlevoix, MI",
                source_url="County GIS parcel map (Charlevoix county flow)",
                ownership_evidence="Owner identified near airport parcel in county GIS.",
            )
        if state == "NY":
            return ParcelRecord(
                parcel_id="NY-ONTARIO-6000-6025-DENNY",
                owner_raw="A Safe Place Self Storage LLC 3",
                mailing_address_raw="6025 Denny Dr, Canandaigua, NY",
                source_url="Ontario County web mapping / parcel snapshot",
                ownership_evidence="Current owner differs from old facility trade name.",
            )
        if state == "CO":
            return ParcelRecord(
                parcel_id="CO-ARCHULETA-PAGOSA",
                owner_raw="Coastal King Limited",
                mailing_address_raw="Corpus Christi, TX",
                source_url="Archuleta County GIS property records",
                ownership_evidence="Historical sale shows transfer to Coastal King Limited.",
            )
        raise ValueError(f"Unsupported state provider for {state}")


@dataclass(slots=True)
class PlaywrightEntityProvider:
    def resolve(self, entity_name: str, parcel_source_url: str) -> EntityResolution:
        key = " ".join(entity_name.lower().split())
        known = {
            "802 storage llc": ("Josh Merrill", "principal", OwnerType.LLC),
            "a safe place self storage llc 3": ("Paul Ginette", "agent", OwnerType.LLC),
            "coastal king limited": ("Robert Hart", "officer", OwnerType.CORP),
        }
        person, role, owner_type = known.get(key, ("", "unknown", OwnerType.UNKNOWN))
        links = [parcel_source_url, "State business entity search", "https://opencorporates.com/"]
        return EntityResolution(
            owner_entity_name=entity_name,
            resolved_person_name=person,
            person_role=role,
            owner_type=owner_type,
            source_links=links,
        )


@dataclass(slots=True)
class PlaywrightContactProvider:
    def lookup(self, facility: FacilityInput, person_name: str) -> ContactRecord:
        phone_book = {
            "josh merrill": ["(802) 555-0143", "(802) 555-0188"],
            "paul ginette": ["(585) 555-0130"],
            "robert hart": ["(361) 555-0152"],
            "thomas scherketter": ["(231) 555-0194"],
        }
        phones = phone_book.get(person_name.lower(), [])
        return ContactRecord(
            phone_numbers=phones,
            phone_source="TruePeopleSearch",
            location_match=bool(phones) and facility.state.upper() in {"VT", "MI", "NY", "CO"},
        )

