"""Shared helpers for the Aus-Land-Data ETL fetchers.

Dependency-free (stdlib only) so it runs on a bare Python 3.x install. HTTP is
done with ``urllib`` and all network calls are defensive: failures are caught
and returned as structured error dicts rather than raising, so a single dead
endpoint never aborts the whole pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SCRIPTS_DIR.parent
CONFIG_PATH = SCRIPTS_DIR / "config" / "land_data_config.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "land-data"


@dataclass
class Site:
    address: str
    lga_name: str
    council_name: str
    lat: float
    lon: float
    buffer_metres: float
    abs_region_type: str
    abs_region_code: str

    @classmethod
    def from_config(cls, cfg: dict) -> "Site":
        s = cfg["site"]
        return cls(
            address=s.get("address", ""),
            lga_name=s.get("lga_name", ""),
            council_name=s.get("council_name", ""),
            lat=float(s.get("lat", 0.0)),
            lon=float(s.get("lon", 0.0)),
            buffer_metres=float(s.get("buffer_metres", 0)),
            abs_region_type=s.get("abs_region_type", "LGA"),
            abs_region_code=str(s.get("abs_region_code", "")),
        )


def load_config(path: Path | None = None) -> dict:
    p = path or CONFIG_PATH
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def log(msg: str) -> None:
    print(f"[land-data] {msg}", flush=True)


def http_request(
    url: str,
    *,
    method: str = "GET",
    params: dict | None = None,
    headers: dict | None = None,
    body: bytes | str | dict | None = None,
    http_cfg: dict | None = None,
):
    """Perform an HTTP request and return parsed JSON (or raw text).

    Returns a tuple ``(ok, data, error)``. ``ok`` is False on any failure and
    ``error`` carries a human-readable message.
    """
    http_cfg = http_cfg or {}
    timeout = http_cfg.get("timeout_seconds", 60)
    retries = http_cfg.get("retries", 3)
    backoff = http_cfg.get("retry_backoff_seconds", 2)
    user_agent = http_cfg.get("user_agent", "Aus-Land-Data-ETL/1.0")

    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}" if "?" not in url else f"{url}&{query}"

    data_bytes: bytes | None = None
    req_headers = {"User-Agent": user_agent, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    if body is not None:
        if isinstance(body, (dict, list)):
            data_bytes = json.dumps(body).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json")
        elif isinstance(body, str):
            data_bytes = body.encode("utf-8")
        else:
            data_bytes = body

    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url, data=data_bytes, headers=req_headers, method=method
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                ctype = resp.headers.get("Content-Type", "")
                if "json" in ctype or raw[:1] in "{[":
                    try:
                        return True, json.loads(raw), ""
                    except json.JSONDecodeError:
                        return True, raw, ""
                return True, raw, ""
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            last_err = f"HTTP {e.code} {e.reason} {detail}".strip()
            # Client errors (4xx) won't fix themselves on retry.
            if 400 <= e.code < 500:
                break
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = f"URL error: {getattr(e, 'reason', e)}"
        except Exception as e:  # noqa: BLE001 - never let a fetcher crash the run
            last_err = f"{type(e).__name__}: {e}"

        if attempt < retries:
            time.sleep(backoff * attempt)

    return False, None, last_err


def arcgis_point_query(
    layer_url: str,
    lon: float,
    lat: float,
    *,
    out_fields: str = "*",
    http_cfg: dict | None = None,
):
    """Query an ArcGIS REST feature layer for features intersecting a WGS84 point."""
    geometry = {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}
    params = {
        "f": "json",
        "geometry": json.dumps(geometry),
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "outSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": "false",
        "where": "1=1",
    }
    url = layer_url.rstrip("/") + "/query"
    return http_request(url, method="GET", params=params, http_cfg=http_cfg)


def arcgis_where_query(
    layer_url: str,
    where: str,
    *,
    out_fields: str = "*",
    page_size: int = 1000,
    max_records: int = 5000,
    order_by: str = "OBJECTID",
    http_cfg: dict | None = None,
):
    """Page through an ArcGIS feature layer using a SQL ``where`` clause.

    Returns ``(records, error)`` where ``records`` is a list of attribute dicts.
    """
    url = layer_url.rstrip("/") + "/query"
    records: list[dict] = []
    offset = 0
    while len(records) < max_records:
        params = {
            "f": "json",
            "where": where,
            "outFields": out_fields,
            "returnGeometry": "false",
            "orderByFields": order_by,
            "resultOffset": offset,
            "resultRecordCount": page_size,
        }
        ok, payload, err = http_request(
            url, method="GET", params=params, http_cfg=http_cfg
        )
        if not ok:
            return records, err
        if isinstance(payload, dict) and payload.get("error"):
            return records, str(payload["error"].get("message", payload["error"]))
        features = payload.get("features", []) if isinstance(payload, dict) else []
        if not features:
            break
        records.extend(f.get("attributes", {}) for f in features)
        exceeded = isinstance(payload, dict) and payload.get("exceededTransferLimit")
        if not exceeded and len(features) < page_size:
            break
        offset += len(features)
    return records[:max_records], ""


def ensure_out_dir(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_json(out_dir: Path, name: str, data) -> Path:
    path = out_dir / f"{name}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"wrote {path}")
    return path


def write_csv(
    out_dir: Path, name: str, rows: list[dict], fieldnames: list[str] | None = None
) -> Path | None:
    if not rows:
        log(f"no rows for {name}.csv (skipped)")
        return None
    fieldnames = fieldnames or sorted({k for r in rows for k in r.keys()})
    path = out_dir / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    log(f"wrote {path} ({len(rows)} rows)")
    return path
