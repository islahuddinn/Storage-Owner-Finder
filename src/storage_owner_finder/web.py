from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from storage_owner_finder.input_modes import load_discovery_request
from storage_owner_finder.models import FacilityInput
from storage_owner_finder.pipeline import StorageOwnerPipeline


BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Storage Owner Finder MVP")


def _run_direct(input_payload: str, output_dir: Path) -> tuple[int, list[dict]]:
    rows = json.loads(input_payload)
    facilities = [
        FacilityInput(
            facility_name=row.get("facility_name", ""),
            address=row["address"],
            city=row["city"],
            state=row["state"],
            county=row.get("county", ""),
        )
        for row in rows
    ]
    pipeline = StorageOwnerPipeline(output_dir=output_dir)
    leads = pipeline.run(facilities)
    return len(leads), [asdict(lead) for lead in leads]


def _run_discovery(mode: str, input_payload: str, output_dir: Path) -> tuple[int, list[dict]]:
    payload = {"mode": mode}
    if mode == "address_list":
        payload["addresses"] = json.loads(input_payload)
    elif mode == "city_state_batch":
        payload["city_state_pairs"] = json.loads(input_payload)
    elif mode == "state_batch":
        payload["states"] = json.loads(input_payload)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    req_path = output_dir / "request.json"
    req_path.parent.mkdir(parents=True, exist_ok=True)
    req_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    request = load_discovery_request(req_path)

    pipeline = StorageOwnerPipeline(output_dir=output_dir)
    leads = pipeline.run_discovery(request)
    return len(leads), [asdict(lead) for lead in leads]


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "default_mode": "address_list",
            "default_payload": json.dumps(
                [
                    {
                        "facility_name": "Killington Road Storage",
                        "address": "1700 Killington Rd",
                        "city": "Killington",
                        "state": "VT",
                        "county": "Rutland",
                    }
                ],
                indent=2,
            ),
        },
    )


@app.post("/run", response_class=HTMLResponse)
def run(
    request: Request,
    mode: str = Form(...),
    payload_json: str = Form(...),
) -> HTMLResponse:
    run_id = uuid4().hex[:8]
    output_dir = BASE_DIR / "web_output" / run_id

    try:
        if mode == "direct_run":
            count, leads = _run_direct(payload_json, output_dir)
        else:
            count, leads = _run_discovery(mode, payload_json, output_dir)
    except Exception as exc:  # noqa: BLE001
        return TEMPLATES.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": str(exc),
                "default_mode": mode,
                "default_payload": payload_json,
            },
            status_code=400,
        )

    return TEMPLATES.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "success": f"Processed {count} facilities",
            "default_mode": mode,
            "default_payload": payload_json,
            "result": leads,
            "csv_path": str(output_dir / "owner_leads.csv"),
            "review_queue_path": str(output_dir / "manual_review_queue.json"),
        },
    )


@app.get("/health", response_class=JSONResponse)
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

