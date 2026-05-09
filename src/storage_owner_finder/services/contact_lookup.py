from __future__ import annotations

from dataclasses import dataclass

from storage_owner_finder.models import ContactRecord, EntityResolution, FacilityInput
from storage_owner_finder.providers.playwright_providers import PlaywrightContactProvider


@dataclass(slots=True)
class ContactLookupService:
    """MVP stub for people-search provider."""
    provider: PlaywrightContactProvider | None = None

    def lookup(self, facility: FacilityInput, resolution: EntityResolution) -> ContactRecord:
        if not resolution.resolved_person_name:
            return ContactRecord(phone_numbers=[], phone_source="none", location_match=False)

        if self.provider is not None:
            return self.provider.lookup(facility, resolution.resolved_person_name)

        phone_book = {
            "josh merrill": ["(802) 555-0143", "(802) 555-0188"],
            "paul ginette": ["(585) 555-0130"],
            "robert hart": ["(361) 555-0152"],
            "thomas scherketter": ["(231) 555-0194"],
        }
        phones = phone_book.get(resolution.resolved_person_name.lower(), [])
        location_match = facility.state.upper() in {"VT", "NY", "CO", "MI"}
        return ContactRecord(
            phone_numbers=phones,
            phone_source="truepeoplesearch_stub",
            location_match=location_match,
        )

