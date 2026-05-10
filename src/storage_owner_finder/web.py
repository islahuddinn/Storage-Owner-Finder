from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from storage_owner_finder.input_modes import load_discovery_request
from storage_owner_finder.models import FacilityInput, OwnerLead
from storage_owner_finder.pipeline import StorageOwnerPipeline

BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

RUN_ID_RE = re.compile(r"^[a-f0-9]{8}$")

app = FastAPI(title="Storage Owner Finder MVP")


def _lead_as_dict(lead: OwnerLead) -> dict:
    d = asdict(lead)
    d["validation_status"] = lead.validation_status.value
    return d


def _parse_direct_rows(payload_json: str) -> list[dict]:
    raw = json.loads(payload_json)
    if isinstance(raw, dict):
        return list(raw.get("addresses", []))
    return list(raw)


def _build_discovery_payload(mode: str, payload_json: str) -> dict:
    raw = json.loads(payload_json)
    opts: dict = {
        "radius_meters": 25_000,
        "max_facilities": 200,
        "use_osm_discovery": True,
        "region": "",
    }
    body: list | None = None

    if isinstance(raw, dict):
        for k in ("radius_meters", "max_facilities", "use_osm_discovery", "region"):
            if k in raw:
                opts[k] = raw[k]
        if mode == "address_list":
            body = list(raw.get("addresses", []))
        elif mode == "city_state_batch":
            if "city" in raw and "state" in raw and "city_state_pairs" not in raw:
                body = [{"city": raw["city"], "state": raw["state"]}]
            else:
                body = list(raw.get("city_state_pairs", []))
        elif mode == "state_batch":
            body = list(raw.get("states", []))
        else:
            body = []
    else:
        body = list(raw)

    payload: dict = {"mode": mode, **opts}
    if mode == "address_list":
        payload["addresses"] = body or []
    elif mode == "city_state_batch":
        payload["city_state_pairs"] = body or []
    elif mode == "state_batch":
        payload["states"] = body or []

    payload["radius_meters"] = int(payload["radius_meters"])
    payload["max_facilities"] = int(payload["max_facilities"])
    payload["use_osm_discovery"] = bool(payload["use_osm_discovery"])
    return payload


def _run_direct(input_payload: str, output_dir: Path) -> tuple[int, list[dict]]:
    rows = _parse_direct_rows(input_payload)
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
    return len(leads), [_lead_as_dict(lead) for lead in leads]


def _run_discovery(mode: str, input_payload: str, output_dir: Path) -> tuple[int, list[dict]]:
    payload = _build_discovery_payload(mode, input_payload)
    req_path = output_dir / "request.json"
    req_path.parent.mkdir(parents=True, exist_ok=True)
    req_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    request = load_discovery_request(req_path)

    pipeline = StorageOwnerPipeline(output_dir=output_dir)
    leads = pipeline.run_discovery(request)
    return len(leads), [_lead_as_dict(lead) for lead in leads]


def _safe_run_dir(run_id: str) -> Path:
    if not RUN_ID_RE.match(run_id):
        raise HTTPException(status_code=400, detail="Invalid run id")
    path = BASE_DIR / "web_output" / run_id
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")
    return path


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
    except json.JSONDecodeError as exc:
        return TEMPLATES.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": f"Invalid JSON: {exc}",
                "default_mode": mode,
                "default_payload": payload_json,
            },
            status_code=400,
        )
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
            "run_id": run_id,
            "result_count": count,
            "default_mode": mode,
            "default_payload": payload_json,
            "result": leads,
        },
    )


@app.get("/download/{run_id}/owner_leads.csv")
def download_csv(run_id: str) -> FileResponse:
    run_dir = _safe_run_dir(run_id)
    path = run_dir / "owner_leads.csv"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="CSV not found")
    return FileResponse(
        path,
        filename="owner_leads.csv",
        media_type="text/csv",
    )


@app.get("/download/{run_id}/manual_review_queue.json")
def download_review_queue(run_id: str) -> FileResponse:
    run_dir = _safe_run_dir(run_id)
    path = run_dir / "manual_review_queue.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Review queue not found")
    return FileResponse(
        path,
        filename="manual_review_queue.json",
        media_type="application/json",
    )


@app.get("/health", response_class=JSONResponse)
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})
