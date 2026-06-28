"""NSW Planning Portal — DA Tracking (ArcGIS REST feature layer).

Pulls development-application records for the configured LGA and lodgement-date
range from the NSW ePlanning DA Tracking spatial service (keyless) and writes
the raw attributes plus a flattened CSV of the key DA fields.

Service: Planning/DA_Tracking/MapServer/0 on mapprod3.environment.nsw.gov.au
"""

from __future__ import annotations

from pathlib import Path

from .common import Site, arcgis_where_query, log, write_csv, write_json


def _fmt_date(val) -> str:
    """DA Tracking dates are strings shaped 'YYYYMMDDHHMMSS' -> 'YYYY-MM-DD'."""
    if val in (None, ""):
        return ""
    s = str(val)
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _normalize(rec: dict) -> dict:
    return {
        "application_number": rec.get("PLANNING_PORTAL_APP_NUMBER", ""),
        "da_number": rec.get("DA_NUMBER", ""),
        "council": rec.get("COUNCIL_NAME", ""),
        "lga": rec.get("LGA_NAME", ""),
        "status": rec.get("STATUS", ""),
        "application_type": rec.get("APPLICATION_TYPE", ""),
        "development_type": rec.get("TYPE_OF_DEVELOPMENT", ""),
        "lodged": _fmt_date(rec.get("LODGEMENT_DATE")),
        "determined": _fmt_date(rec.get("DETERMINED_DATE")),
        "cost_of_development": rec.get("COST_OF_DEVELOPMENT", ""),
        "address": rec.get("SITE_ADDRESS") or rec.get("PRIMARY_ADDRESS", ""),
        "suburb": rec.get("SUBURBNAME", ""),
        "postcode": rec.get("POSTCODE", ""),
        "description": rec.get("DEVELOPMENT_DETAILED_DESC", ""),
    }


def _build_where(cfg: dict, site: Site) -> str:
    lga_field = cfg.get("lga_field", "LGA_NAME")
    date_field = cfg.get("date_field", "LODGEMENT_DATE")
    clauses = []
    if site.lga_name:
        clauses.append(f"UPPER({lga_field}) = '{site.lga_name.upper()}'")
    # LODGEMENT_DATE is a string column shaped YYYYMMDDHHMMSS, so compare
    # lexicographically against zero-padded string bounds.
    if cfg.get("lodged_from"):
        frm = cfg["lodged_from"].replace("-", "") + "000000"
        clauses.append(f"{date_field} >= '{frm}'")
    if cfg.get("lodged_to"):
        to = cfg["lodged_to"].replace("-", "") + "235959"
        clauses.append(f"{date_field} <= '{to}'")
    return " AND ".join(clauses) if clauses else "1=1"


def fetch(source_cfg: dict, site: Site, http_cfg: dict, out_dir: Path) -> dict:
    layer_url = source_cfg["layer_url"]
    where = _build_where(source_cfg, site)
    log(f"NSW DA Tracking where: {where}")

    records, err = arcgis_where_query(
        layer_url,
        where,
        out_fields=source_cfg.get("out_fields", "*"),
        page_size=source_cfg.get("page_size", 1000),
        max_records=source_cfg.get("max_records", 5000),
        http_cfg=http_cfg,
    )

    write_json(out_dir, "nsw_planning_da_raw", records)
    normalized = [_normalize(r) for r in records]
    write_csv(out_dir, "nsw_planning_da", normalized)

    return {
        "source": "nsw_planning_da",
        "ok": not err,
        "record_count": len(records),
        "error": err,
    }
