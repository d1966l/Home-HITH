"""NSW land zoning — ePlanning EPI Primary Planning Layers (ArcGIS REST).

Queries the Land Zoning feature layer at the subject site's point and records
the zone code/name plus any other returned attributes.
"""

from __future__ import annotations

from pathlib import Path

from .common import Site, arcgis_point_query, log, write_csv, write_json


def _zone_summary(attrs: dict) -> dict:
    def g(*keys, default=""):
        for k in keys:
            for ak, av in attrs.items():
                if ak.upper() == k.upper() and av not in (None, ""):
                    return av
        return default

    return {
        "zone_code": g("SYM_CODE", "ZONE", "LAND_ZONE_CODE"),
        "zone_name": g("LAND_ZONE", "LANDUSE", "ZONE_DESC", "LABEL"),
        "lga": g("LGA_NAME", "LGA"),
        "epi_name": g("EPI_NAME", "PLAN_NAME"),
        "purpose": g("PURPOSE", "COMMENTS"),
    }


def fetch(source_cfg: dict, site: Site, http_cfg: dict, out_dir: Path) -> dict:
    layer_url = source_cfg["layer_url"]
    out_fields = source_cfg.get("out_fields", "*")

    log(f"Querying land zoning at ({site.lon}, {site.lat}) ...")
    ok, payload, err = arcgis_point_query(
        layer_url, site.lon, site.lat, out_fields=out_fields, http_cfg=http_cfg
    )
    if not ok:
        write_json(out_dir, "nsw_zoning_raw", {"error": err})
        return {"source": "nsw_zoning", "ok": False, "feature_count": 0, "error": err}

    features = (payload or {}).get("features", []) if isinstance(payload, dict) else []
    write_json(out_dir, "nsw_zoning_raw", payload)

    rows = [_zone_summary(f.get("attributes", {})) for f in features]
    write_csv(out_dir, "nsw_zoning", rows)

    primary = rows[0] if rows else {}
    return {
        "source": "nsw_zoning",
        "ok": True,
        "feature_count": len(features),
        "zone_code": primary.get("zone_code", ""),
        "zone_name": primary.get("zone_name", ""),
        "error": "",
    }
