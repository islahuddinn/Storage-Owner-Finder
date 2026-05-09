from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(slots=True)
class TranscriptFixture:
    case_id: str
    facility_name: str
    address: str
    city: str
    state: str
    county: str
    expected_path: str
    parcel_owner_raw: str
    expected_person: str
    notes: str


def load_transcript_fixtures() -> List[TranscriptFixture]:
    fixture_path = (
        Path(__file__).parent / "fixtures" / "transcript_cases.json"
    )
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    return [TranscriptFixture(**row) for row in data]

