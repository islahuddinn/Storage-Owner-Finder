from __future__ import annotations

from abc import ABC, abstractmethod

from storage_owner_finder.models import FacilityInput, ParcelRecord


class GISConnector(ABC):
    @abstractmethod
    def lookup_parcel(self, facility: FacilityInput) -> ParcelRecord:
        """Resolve a parcel record from a facility input."""

