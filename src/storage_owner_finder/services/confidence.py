from __future__ import annotations

from dataclasses import dataclass

from storage_owner_finder.models import (
    ContactRecord,
    EntityResolution,
    ParcelRecord,
    ScoredResult,
    ValidationStatus,
)


@dataclass(slots=True)
class ConfidenceEngine:
    def score(
        self,
        parcel: ParcelRecord,
        entity: EntityResolution,
        contact: ContactRecord,
    ) -> ScoredResult:
        score = 0.0
        reasons: list[str] = []

        if entity.owner_entity_name and entity.owner_entity_name.lower() in parcel.owner_raw.lower():
            score += 0.35
            reasons.append("owner_entity_matches_parcel")

        if entity.resolved_person_name and entity.person_role in {"principal", "officer", "agent", "direct"}:
            score += 0.25
            reasons.append("resolved_person_role_linked")

        if parcel.mailing_address_raw:
            score += 0.20
            reasons.append("mailing_address_present")

        if "sold" not in parcel.ownership_evidence.lower():
            score += 0.10
            reasons.append("no_transfer_conflict")

        if contact.location_match and contact.phone_numbers:
            score += 0.10
            reasons.append("contact_location_aligned")

        score = round(min(score, 1.0), 2)

        if score >= 0.85:
            status = ValidationStatus.AUTO_PASS
        elif score >= 0.60:
            status = ValidationStatus.MANUAL_REVIEW
        else:
            status = ValidationStatus.REJECTED

        return ScoredResult(confidence_score=score, validation_status=status, reason_codes=reasons)

