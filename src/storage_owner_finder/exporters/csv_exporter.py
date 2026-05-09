from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from storage_owner_finder.models import OwnerLead


CSV_COLUMNS = [
    "input_facility_name",
    "input_address",
    "city",
    "state",
    "county",
    "parcel_id",
    "parcel_owner_raw",
    "mailing_address_raw",
    "owner_entity_name",
    "resolved_person_name",
    "person_role",
    "phone_numbers",
    "phone_source",
    "ownership_evidence",
    "source_links",
    "confidence_score",
    "validation_status",
    "reason_codes",
    "review_notes",
    "extraction_timestamp",
]


@dataclass(slots=True)
class CSVExporter:
    output_path: Path

    def export(self, leads: Iterable[OwnerLead]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for lead in leads:
                row = asdict(lead)
                row["phone_numbers"] = "|".join(lead.phone_numbers)
                row["source_links"] = "|".join(lead.source_links)
                row["reason_codes"] = "|".join(lead.reason_codes)
                row["validation_status"] = lead.validation_status.value
                writer.writerow(row)

