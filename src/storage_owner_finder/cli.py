from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from storage_owner_finder.input_modes import load_discovery_request
from storage_owner_finder.models import FacilityInput
from storage_owner_finder.pipeline import StorageOwnerPipeline
from storage_owner_finder.spec import load_transcript_fixtures


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Storage Owner Finder MVP CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run MVP pipeline")
    run_cmd.add_argument("--input-json", required=True, help="Path to facility input JSON file")
    run_cmd.add_argument("--output-dir", default="output", help="Output directory")

    discover_cmd = sub.add_parser("discover-run", help="Discover facilities then run pipeline")
    discover_cmd.add_argument(
        "--request-json",
        required=True,
        help="Path to discovery request JSON with mode: address_list/city_state_batch/state_batch",
    )
    discover_cmd.add_argument("--output-dir", default="output", help="Output directory")

    sub.add_parser("fixtures", help="Print transcript fixtures")
    return parser.parse_args()


def _load_inputs(path: Path) -> list[FacilityInput]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [
        FacilityInput(
            facility_name=row["facility_name"],
            address=row["address"],
            city=row["city"],
            state=row["state"],
            county=row.get("county", ""),
        )
        for row in rows
    ]


def main() -> None:
    args = _parse_args()
    if args.command == "fixtures":
        fixtures = [asdict(fixture) for fixture in load_transcript_fixtures()]
        print(json.dumps(fixtures, indent=2))
        return

    pipeline = StorageOwnerPipeline(output_dir=Path(args.output_dir))
    if args.command == "discover-run":
        request = load_discovery_request(Path(args.request_json))
        leads = pipeline.run_discovery(request)
    else:
        inputs = _load_inputs(Path(args.input_json))
        leads = pipeline.run(inputs)
    print(f"Processed {len(leads)} facilities.")
    print(f"CSV: {Path(args.output_dir) / 'owner_leads.csv'}")
    print(f"Review queue: {Path(args.output_dir) / 'manual_review_queue.json'}")


if __name__ == "__main__":
    main()

