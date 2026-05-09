from __future__ import annotations

import re
from dataclasses import dataclass

from storage_owner_finder.models import EntityResolution, OwnerType, ParcelRecord
from storage_owner_finder.providers.playwright_providers import PlaywrightEntityProvider


@dataclass(slots=True)
class OwnerResolutionService:
    provider: PlaywrightEntityProvider | None = None

    def resolve(self, parcel: ParcelRecord) -> EntityResolution:
        raw = parcel.owner_raw.strip()
        lowered = raw.lower()

        if any(token in lowered for token in ["llc", "limited", "inc", "corp"]):
            return self._resolve_entity(raw, parcel)

        return EntityResolution(
            owner_entity_name=raw,
            resolved_person_name=self._normalize_person_name(raw),
            person_role="direct",
            owner_type=OwnerType.INDIVIDUAL,
            source_links=[parcel.source_url],
        )

    def _resolve_entity(self, entity_name: str, parcel: ParcelRecord) -> EntityResolution:
        if self.provider is not None:
            return self.provider.resolve(entity_name=entity_name, parcel_source_url=parcel.source_url)

        entity_key = re.sub(r"\s+", " ", entity_name.lower()).strip()

        # Transcript-grounded deterministic mappings for MVP.
        known = {
            "802 storage llc": ("Josh Merrill", "principal", OwnerType.LLC),
            "a safe place self storage llc 3": ("Paul Ginette", "agent", OwnerType.LLC),
            "coastal king limited": ("Robert Hart", "officer", OwnerType.CORP),
        }
        person, role, owner_type = known.get(
            entity_key, ("", "unknown", OwnerType.UNKNOWN)
        )

        source_links = [parcel.source_url]
        if owner_type in (OwnerType.LLC, OwnerType.CORP):
            source_links.append("https://opencorporates.com/")

        return EntityResolution(
            owner_entity_name=entity_name,
            resolved_person_name=person,
            person_role=role,
            owner_type=owner_type,
            source_links=source_links,
        )

    @staticmethod
    def _normalize_person_name(name: str) -> str:
        name = name.replace("Family", "").strip()
        return " ".join(name.split())

