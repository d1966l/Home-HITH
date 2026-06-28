"""BOCSAR LGA crime statistics via the data.nsw.gov.au CKAN API.

BOCSAR (NSW Bureau of Crime Statistics and Research) publishes recorded-crime
data on data.nsw.gov.au. This fetcher:

1. If a ``resource_id`` is configured, pulls rows straight from the CKAN
   datastore (``datastore_search``), filtered to the configured LGA.
2. Otherwise it runs ``package_search`` to discover candidate BOCSAR LGA
   datasets and writes the catalogue so a resource_id can be pinned in config.
"""

from __future__ import annotations

from pathlib import Path

from .common import Site, http_request, log, write_csv, write_json


def _discover(ckan_base: str, query: str, http_cfg: dict) -> tuple[list[dict], str]:
    url = f"{ckan_base.rstrip('/')}/package_search"
    ok, payload, err = http_request(
        url, method="GET", params={"q": query, "rows": 50}, http_cfg=http_cfg
    )
    if not ok or not isinstance(payload, dict):
        return [], err or "package_search failed"
    results = payload.get("result", {}).get("results", [])
    catalogue = []
    for pkg in results:
        for res in pkg.get("resources", []):
            catalogue.append(
                {
                    "dataset": pkg.get("title", ""),
                    "resource_name": res.get("name", ""),
                    "resource_id": res.get("id", ""),
                    "format": res.get("format", ""),
                    "datastore_active": res.get("datastore_active", False),
                    "url": res.get("url", ""),
                }
            )
    return catalogue, ""


def _datastore_rows(
    ckan_base: str,
    resource_id: str,
    lga_field: str,
    lga: str,
    limit: int,
    http_cfg: dict,
) -> tuple[list[dict], str]:
    url = f"{ckan_base.rstrip('/')}/datastore_search"
    params = {"resource_id": resource_id, "limit": limit}
    if lga and lga_field:
        params["filters"] = '{"%s": "%s"}' % (lga_field, lga)
    ok, payload, err = http_request(url, method="GET", params=params, http_cfg=http_cfg)
    if not ok or not isinstance(payload, dict):
        return [], err or "datastore_search failed"
    records = payload.get("result", {}).get("records", [])
    return records, ""


def fetch(source_cfg: dict, site: Site, http_cfg: dict, out_dir: Path) -> dict:
    ckan_base = source_cfg["ckan_base"]
    resource_id = source_cfg.get("resource_id", "").strip()
    lga_field = source_cfg.get("lga_field", "LGA")
    limit = source_cfg.get("limit", 1000)
    lga = site.lga_name

    if resource_id:
        log(f"BOCSAR datastore_search resource={resource_id} LGA={lga} ...")
        records, err = _datastore_rows(
            ckan_base, resource_id, lga_field, lga, limit, http_cfg
        )
        write_json(out_dir, "bocsar_crime_raw", records)
        write_csv(out_dir, "bocsar_crime", records)
        return {
            "source": "bocsar_crime",
            "ok": not err,
            "record_count": len(records),
            "mode": "datastore",
            "error": err,
        }

    log("BOCSAR resource_id not set — discovering datasets via package_search ...")
    catalogue, err = _discover(
        ckan_base, source_cfg.get("package_search_query", "BOCSAR LGA crime"), http_cfg
    )
    write_json(out_dir, "bocsar_catalogue_raw", catalogue)
    write_csv(out_dir, "bocsar_catalogue", catalogue)
    if catalogue and not err:
        log(
            "Set 'bocsar_crime.resource_id' in land_data_config.json to a "
            "datastore-active resource from bocsar_catalogue.csv, then re-run."
        )
    return {
        "source": "bocsar_crime",
        "ok": bool(catalogue),
        "record_count": len(catalogue),
        "mode": "catalogue",
        "error": err,
    }
