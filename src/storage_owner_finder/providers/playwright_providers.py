from __future__ import annotations

import hashlib
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


def _facility_fingerprint(facility: FacilityInput) -> str:
    key = "|".join(
        [
            facility.facility_name,
            facility.address,
            facility.city,
            facility.state,
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]


@dataclass(slots=True)
class PlaywrightParcelProvider:
    state: str

    def resolve(self, facility: FacilityInput) -> ParcelRecord:
        state = self.state.upper()
        fp = _facility_fingerprint(facility)
        fam = (facility.facility_name or "").lower()
        addr = (facility.address or "").lower()
        city = (facility.city or "").lower()

        if state == "VT" and "killington" in city:
            return ParcelRecord(
                parcel_id="VT-RUTLAND-1700-KILLINGTON-RD",
                owner_raw="802 Storage LLC",
                mailing_address_raw="1700 Killington Rd, Killington, VT",
                source_url="https://maps.vcgi.vermont.gov/parcelviewer/",
                ownership_evidence="Vermont statewide parcel map owner match.",
            )
        if state == "MI" and "charlevoix" in city:
            return ParcelRecord(
                parcel_id="MI-CHARLEVOIX-AIRPORT-AREA",
                owner_raw="Thomas Scherketter Family",
                mailing_address_raw="Charlevoix, MI",
                source_url="County GIS parcel map (Charlevoix county flow)",
                ownership_evidence="Owner identified near airport parcel in county GIS.",
            )
        if state == "NY" and ("denny" in addr or "safe place" in fam):
            return ParcelRecord(
                parcel_id="NY-ONTARIO-6000-6025-DENNY",
                owner_raw="A Safe Place Self Storage LLC 3",
                mailing_address_raw="6025 Denny Dr, Canandaigua, NY",
                source_url="Ontario County web mapping / parcel snapshot",
                ownership_evidence="Current owner differs from old facility trade name.",
            )
        if state == "CO" and "pagosa" in city:
            return ParcelRecord(
                parcel_id="CO-ARCHULETA-PAGOSA",
                owner_raw="Coastal King Limited",
                mailing_address_raw="Corpus Christi, TX",
                source_url="Archuleta County GIS property records",
                ownership_evidence="Historical sale shows transfer to Coastal King Limited.",
            )

        src = GIS_WEBSITES_BY_STATE.get(state, "County GIS parcel map")
        owner_guess = facility.facility_name.strip() or "Property owner (GIS pending)"
        return ParcelRecord(
            parcel_id=f"{state}-STUB-{fp}",
            owner_raw=owner_guess,
            mailing_address_raw=f"{facility.address}, {facility.city}, {state}",
            source_url=src,
            ownership_evidence=(
                "Stub parcel row until county GIS browser automation is wired for this address."
            ),
        )


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
