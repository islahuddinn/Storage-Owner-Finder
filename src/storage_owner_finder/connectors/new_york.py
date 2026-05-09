from __future__ import annotations

from storage_owner_finder.connectors.base import GISConnector
from storage_owner_finder.models import FacilityInput, ParcelRecord
from storage_owner_finder.providers.playwright_providers import PlaywrightParcelProvider


class NewYorkGISConnector(GISConnector):
    def __init__(self, provider: PlaywrightParcelProvider | None = None) -> None:
        self.provider = provider or PlaywrightParcelProvider(state="NY")

    def lookup_parcel(self, facility: FacilityInput) -> ParcelRecord:
        if facility.state.upper() != "NY":
            raise ValueError("NewYorkGISConnector can only process NY facilities.")
        return self.provider.resolve(facility)

