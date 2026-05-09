from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from storage_owner_finder.models import OwnerLead, ValidationStatus


@dataclass(slots=True)
class ManualReviewQueue:
    output_path: Path

    def push(self, lead: OwnerLead) -> None:
        if lead.validation_status != ValidationStatus.MANUAL_REVIEW:
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        items = self._read_items()
        items.append(asdict(lead))
        self.output_path.write_text(json.dumps(items, indent=2), encoding="utf-8")

    def bulk_push(self, leads: Iterable[OwnerLead]) -> None:
        for lead in leads:
            self.push(lead)

    def _read_items(self) -> list[dict]:
        if not self.output_path.exists():
            return []
        text = self.output_path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        return json.loads(text)

