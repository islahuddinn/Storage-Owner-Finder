from __future__ import annotations

from storage_owner_finder.connectors.base import GISConnector
from storage_owner_finder.models import FacilityInput, ParcelRecord
from storage_owner_finder.providers.playwright_providers import PlaywrightParcelProvider


class ColoradoGISConnector(GISConnector):
    def __init__(self, provider: PlaywrightParcelProvider | None = None) -> None:
        self.provider = provider or PlaywrightParcelProvider(state="CO")

    def lookup_parcel(self, facility: FacilityInput) -> ParcelRecord:
        if facility.state.upper() != "CO":
            raise ValueError("ColoradoGISConnector can only process CO facilities.")
        return self.provider.resolve(facility)

