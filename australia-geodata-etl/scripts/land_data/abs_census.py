"""ABS Census data via the ABS Data API (SDMX-JSON).

Pulls a Census dataflow (e.g. C21_G01 — selected person characteristics) for
the configured region from the Australian Bureau of Statistics Data API and
flattens the SDMX-JSON observations into tidy rows.

API: https://api.data.abs.gov.au  (Data API, SDMX-JSON)
"""

from __future__ import annotations

from pathlib import Path

from .common import Site, http_request, log, write_csv, write_json


def _set_dim(row: dict, dim: dict, idx) -> None:
    name = dim.get("id") or dim.get("name") or "DIM"
    values = dim.get("values", [])
    if isinstance(idx, int) and 0 <= idx < len(values):
        row[name] = values[idx].get("name")
        row[f"{name}_id"] = values[idx].get("id")
    else:
        row[name] = idx


def _flatten_sdmx(payload: dict) -> list[dict]:
    """Flatten SDMX-JSON (1.0 flat-observations or 2.0 series) into tidy rows."""
    try:
        data = payload.get("data", payload)
        datasets = data.get("dataSets", [])
        structures = data.get("structures")
        if structures is None and "structure" in data:
            structures = [data["structure"]]
        if not datasets or not structures:
            return []

        rows: list[dict] = []
        for ds in datasets:
            struct = (
                structures[ds.get("structure", 0)]
                if isinstance(structures, list)
                else structures
            )
            dims = struct.get("dimensions", {})
            series_dims = dims.get("series", [])
            obs_dims = dims.get("observation", [])

            # SDMX-JSON 1.0 style: flat observations on the dataset.
            flat_obs = ds.get("observations")
            if flat_obs:
                for okey, oval in flat_obs.items():
                    row: dict = {}
                    for d, i in zip(obs_dims, [int(x) for x in okey.split(":")]):
                        _set_dim(row, d, i)
                    row["value"] = oval[0] if oval else None
                    rows.append(row)
                continue

            # SDMX-JSON 2.0 style: series keyed by series-dim indices.
            for skey, sobj in ds.get("series", {}).items():
                base: dict = {}
                sidx = [int(x) for x in skey.split(":")] if skey else []
                for d, i in zip(series_dims, sidx):
                    _set_dim(base, d, i)
                for okey, oval in sobj.get("observations", {}).items():
                    row = dict(base)
                    oidx = [int(x) for x in okey.split(":")] if okey else []
                    for d, i in zip(obs_dims, oidx):
                        _set_dim(row, d, i)
                    row["value"] = oval[0] if oval else None
                    rows.append(row)
        return rows
    except Exception as e:  # noqa: BLE001 - flattening must never crash the run
        log(f"ABS flatten failed: {type(e).__name__}: {e}")
        return []


def fetch(source_cfg: dict, site: Site, http_cfg: dict, out_dir: Path) -> dict:
    base = source_cfg["base_url"].rstrip("/")
    dataflow = source_cfg["dataflow"]
    data_key = source_cfg.get("data_key", "all")
    start = source_cfg.get("start_period")
    end = source_cfg.get("end_period")
    name = source_cfg.get("output_name", "abs_census")
    source_name = source_cfg.get("source_name", "abs_census")

    # If data_key uses a region placeholder, inject the configured region code.
    data_key = data_key.replace("{region}", site.abs_region_code)

    url = f"{base}/data/{dataflow}/{data_key}"
    params = {"format": "jsondata"}
    if start:
        params["startPeriod"] = start
    if end:
        params["endPeriod"] = end

    headers = {"Accept": "application/vnd.sdmx.data+json"}
    log(f"ABS Data API {dataflow} key={data_key} ...")
    ok, payload, err = http_request(
        url, method="GET", params=params, headers=headers, http_cfg=http_cfg
    )
    if not ok:
        write_json(out_dir, f"{name}_raw", {"error": err})
        return {"source": source_name, "ok": False, "record_count": 0, "error": err}

    write_json(out_dir, f"{name}_raw", payload)
    rows = _flatten_sdmx(payload) if isinstance(payload, dict) else []
    write_csv(out_dir, name, rows)

    return {
        "source": source_name,
        "ok": True,
        "record_count": len(rows),
        "error": "",
    }
