"""NSW hazard layers — bushfire-prone land and flood planning (ArcGIS REST).

Queries each configured hazard feature layer at the subject site's point. A
returned feature means the site intersects that hazard category (e.g. a
bushfire vegetation buffer or a flood-planning extent).
"""

from __future__ import annotations

from pathlib import Path

from .common import Site, arcgis_point_query, log, write_csv, write_json


def _flatten(name: str, features: list[dict]) -> list[dict]:
    rows = []
    for f in features:
        attrs = f.get("attributes", {}) if isinstance(f, dict) else {}
        row = {"hazard_layer": name, "affected": True}
        for k, v in attrs.items():
            row[k] = v
        rows.append(row)
    if not features:
        rows.append({"hazard_layer": name, "affected": False})
    return rows


def fetch(source_cfg: dict, site: Site, http_cfg: dict, out_dir: Path) -> dict:
    layers = source_cfg.get("layers", [])
    raw: dict = {}
    all_rows: list[dict] = []
    affected: list[str] = []
    errors: list[str] = []

    for layer in layers:
        name = layer.get("name", "hazard")
        layer_url = layer.get("layer_url", "")
        out_fields = layer.get("out_fields", "*")
        if not layer_url:
            continue
        log(f"Querying hazard layer '{name}' at site point ...")
        ok, payload, err = arcgis_point_query(
            layer_url, site.lon, site.lat, out_fields=out_fields, http_cfg=http_cfg
        )
        if not ok:
            errors.append(f"{name}: {err}")
            raw[name] = {"error": err}
            continue
        features = (
            (payload or {}).get("features", []) if isinstance(payload, dict) else []
        )
        raw[name] = payload
        if features:
            affected.append(name)
        all_rows.extend(_flatten(name, features))

    write_json(out_dir, "nsw_hazards_raw", raw)
    write_csv(out_dir, "nsw_hazards", all_rows)

    return {
        "source": "nsw_hazards",
        "ok": not errors or len(errors) < len(layers),
        "layers_checked": len(layers),
        "affected_layers": affected,
        "error": "; ".join(errors),
    }
