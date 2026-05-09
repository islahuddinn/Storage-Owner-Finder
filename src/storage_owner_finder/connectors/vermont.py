from __future__ import annotations

from dataclasses import dataclass

from storage_owner_finder.connectors.base import GISConnector
from storage_owner_finder.models import FacilityInput, ParcelRecord
from storage_owner_finder.providers.playwright_providers import PlaywrightParcelProvider


@dataclass(slots=True)
class VermontParcelProvider:
    """Stub provider representing Vermont statewide parcel map integration."""

    def resolve(self, facility: FacilityInput) -> ParcelRecord:
        # Deterministic seed data grounded in transcript example.
        if "killington" not in facility.city.lower() and "killington" not in facility.address.lower():
            raise ValueError(
                "Vermont connector currently supports Killington pattern inputs for MVP."
            )

        return ParcelRecord(
            parcel_id="VT-RUTLAND-1700-KILLINGTON-RD",
            owner_raw="802 Storage LLC",
            mailing_address_raw="1700 Killington Rd, Killington, VT",
            source_url="https://maps.vcgi.vermont.gov/parcelviewer/",
            ownership_evidence="Parcel owner 802 Storage LLC; mailing matches Killington address.",
            last_sale_date="",
        )


class VermontGISConnector(GISConnector):
    def __init__(self, provider: VermontParcelProvider | PlaywrightParcelProvider | None = None) -> None:
        self.provider = provider or PlaywrightParcelProvider(state="VT")

    def lookup_parcel(self, facility: FacilityInput) -> ParcelRecord:
        if facility.state.upper() != "VT":
            raise ValueError("VermontGISConnector can only process VT facilities.")
        return self.provider.resolve(facility)

