from __future__ import annotations

import json
from pathlib import Path

from storage_owner_finder.models import DiscoveryRequest, InputMode


def load_discovery_request(path: Path) -> DiscoveryRequest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mode = InputMode(payload["mode"])
    return DiscoveryRequest(
        mode=mode,
        addresses=payload.get("addresses", []),
        city_state_pairs=payload.get("city_state_pairs", []),
        states=payload.get("states", []),
        region=payload.get("region", ""),
    )

