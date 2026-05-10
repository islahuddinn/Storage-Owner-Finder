from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List


class OwnerType(str, Enum):
    INDIVIDUAL = "individual"
    LLC = "llc"
    CORP = "corp"
    UNKNOWN = "unknown"


class ValidationStatus(str, Enum):
    AUTO_PASS = "auto_pass"
    MANUAL_REVIEW = "manual_review"
    REJECTED = "rejected"


class InputMode(str, Enum):
    ADDRESS_LIST = "address_list"
    CITY_STATE_BATCH = "city_state_batch"
    STATE_BATCH = "state_batch"


@dataclass(slots=True)
class FacilityInput:
    facility_name: str
    address: str
    city: str
    state: str
    county: str = ""


@dataclass(slots=True)
class DiscoveryRequest:
    mode: InputMode
    addresses: List[dict] = field(default_factory=list)
    city_state_pairs: List[dict] = field(default_factory=list)
    states: List[str] = field(default_factory=list)
    region: str = ""
    # OSM discovery (Nominatim + Overpass): find all mapped self-storage POIs in area
    radius_meters: int = 25_000
    max_facilities: int = 200
    use_osm_discovery: bool = True


@dataclass(slots=True)
class ParcelRecord:
    parcel_id: str
    owner_raw: str
    mailing_address_raw: str
    source_url: str
    ownership_evidence: str = ""
    last_sale_date: str = ""


@dataclass(slots=True)
class EntityResolution:
    owner_entity_name: str
    resolved_person_name: str
    person_role: str
    owner_type: OwnerType
    source_links: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ContactRecord:
    phone_numbers: List[str]
    phone_source: str
    location_match: bool = False


@dataclass(slots=True)
class ScoredResult:
    confidence_score: float
    validation_status: ValidationStatus
    reason_codes: List[str]


@dataclass(slots=True)
class OwnerLead:
    input_facility_name: str
    input_address: str
    city: str
    state: str
    county: str
    parcel_id: str
    parcel_owner_raw: str
    mailing_address_raw: str
    owner_entity_name: str
    resolved_person_name: str
    person_role: str
    phone_numbers: List[str]
    phone_source: str
    ownership_evidence: str
    source_links: List[str]
    confidence_score: float
    validation_status: ValidationStatus
    reason_codes: List[str]
    review_notes: str = ""
    extraction_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

