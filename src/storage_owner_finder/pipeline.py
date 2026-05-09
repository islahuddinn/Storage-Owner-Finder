from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

from storage_owner_finder.connectors.base import GISConnector
from storage_owner_finder.connectors.colorado import ColoradoGISConnector
from storage_owner_finder.connectors.michigan import MichiganGISConnector
from storage_owner_finder.connectors.new_york import NewYorkGISConnector
from storage_owner_finder.connectors.vermont import VermontGISConnector
from storage_owner_finder.discovery import FacilityDiscoveryService
from storage_owner_finder.exporters.csv_exporter import CSVExporter
from storage_owner_finder.models import DiscoveryRequest, FacilityInput, OwnerLead
from storage_owner_finder.providers.playwright_providers import (
    PlaywrightContactProvider,
    PlaywrightEntityProvider,
)
from storage_owner_finder.services.confidence import ConfidenceEngine
from storage_owner_finder.services.contact_lookup import ContactLookupService
from storage_owner_finder.services.owner_resolution import OwnerResolutionService
from storage_owner_finder.services.review_queue import ManualReviewQueue


@dataclass(slots=True)
class StorageOwnerPipeline:
    output_dir: Path
    discovery: FacilityDiscoveryService = field(init=False)
    connectors: dict[str, GISConnector] = field(init=False)
    owner_resolution: OwnerResolutionService = field(init=False)
    contact_lookup: ContactLookupService = field(init=False)
    confidence_engine: ConfidenceEngine = field(init=False)
    csv_exporter: CSVExporter = field(init=False)
    review_queue: ManualReviewQueue = field(init=False)

    def __post_init__(self) -> None:
        self.discovery = FacilityDiscoveryService()
        self.connectors = {
            "VT": VermontGISConnector(),
            "MI": MichiganGISConnector(),
            "NY": NewYorkGISConnector(),
            "CO": ColoradoGISConnector(),
        }
        self.owner_resolution = OwnerResolutionService(provider=PlaywrightEntityProvider())
        self.contact_lookup = ContactLookupService(provider=PlaywrightContactProvider())
        self.confidence_engine = ConfidenceEngine()
        self.csv_exporter = CSVExporter(self.output_dir / "owner_leads.csv")
        self.review_queue = ManualReviewQueue(self.output_dir / "manual_review_queue.json")

    def run_discovery(self, request: DiscoveryRequest) -> List[OwnerLead]:
        facilities = self.discovery.discover(request)
        return self.run(facilities)

    def run(self, facilities: Iterable[FacilityInput]) -> List[OwnerLead]:
        leads: list[OwnerLead] = []
        for facility in facilities:
            lead = self._process_facility(facility)
            leads.append(lead)

        self.csv_exporter.export(leads)
        self.review_queue.bulk_push(leads)
        return leads

    def _process_facility(self, facility: FacilityInput) -> OwnerLead:
        state = facility.state.upper()
        connector = self.connectors.get(state)
        if connector is None:
            raise ValueError(f"No connector configured for state {state}")

        parcel = connector.lookup_parcel(facility)
        resolution = self.owner_resolution.resolve(parcel)
        contact = self.contact_lookup.lookup(facility, resolution)
        scored = self.confidence_engine.score(parcel, resolution, contact)

        return OwnerLead(
            input_facility_name=facility.facility_name,
            input_address=facility.address,
            city=facility.city,
            state=facility.state,
            county=facility.county,
            parcel_id=parcel.parcel_id,
            parcel_owner_raw=parcel.owner_raw,
            mailing_address_raw=parcel.mailing_address_raw,
            owner_entity_name=resolution.owner_entity_name,
            resolved_person_name=resolution.resolved_person_name,
            person_role=resolution.person_role,
            phone_numbers=contact.phone_numbers,
            phone_source=contact.phone_source,
            ownership_evidence=parcel.ownership_evidence,
            source_links=resolution.source_links,
            confidence_score=scored.confidence_score,
            validation_status=scored.validation_status,
            reason_codes=scored.reason_codes,
        )

