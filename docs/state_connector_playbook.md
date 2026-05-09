# State Connector Playbook (MI, NY, CO)

This template defines how to add connectors after Vermont.

## Connector contract

Each state connector should implement:

- Input: `FacilityInput`
- Output: `ParcelRecord`
- Guarantees:
  - stable `parcel_id`
  - `owner_raw` from current parcel record
  - `mailing_address_raw`
  - source URL and ownership evidence text

## Required modules per state

- `connectors/<state>.py` for GIS access and parcel extraction
- owner resolution overrides (if registry is state-specific)
- optional fallback chain for officer/principal extraction
- selector config and retry strategy

## Michigan (next)

- Primary flow: person-owner direct path
- County GIS variability is high; build per-county selector profiles
- Confidence emphasis: person name + mailing address consistency

## New York

- Must guard against stale facility-brand owner names
- Always include ownership history checks where available
- Entity search often has weaker principal details; use officer fallback

## Colorado

- Expect deeper entity chains (LLC -> GP -> management company -> officer)
- Implement max-depth traversal with cycle protection
- Confidence decreases with every unresolved hop

## Implementation checklist

1. Add deterministic fixture case to `fixtures/transcript_cases.json`.
2. Add state connector with provider abstraction.
3. Add state-specific tests:
   - happy path
   - search fallback path
   - stale owner trap prevention
4. Add source provenance fields to output.
5. Validate confidence bucket distribution on 20 sample leads.

