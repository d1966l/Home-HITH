"""Aus-Land-Data ETL orchestrator.

Fetches NSW planning, spatial-hazard and statistical context for the subject
property and writes everything under ``outputs/land-data/``.

Sources:
  * NSW Planning Portal DA API   (development applications)
  * NSW land zoning layer        (ePlanning EPI Primary Planning Layers)
  * Bushfire + flood hazards     (ePlanning hazard ArcGIS layers)
  * BOCSAR LGA crime statistics  (data.nsw.gov.au CKAN)
  * ABS Census data              (ABS Data API, SDMX-JSON)

Usage:
  python fetch_land_data.py                 # run every enabled source
  python fetch_land_data.py --only nsw_zoning nsw_hazards
  python fetch_land_data.py --list          # list sources
  python fetch_land_data.py --dry-run       # show plan, make no network calls
  python fetch_land_data.py --config path/to/config.json
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Allow running as a script (python fetch_land_data.py) or as a module.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from land_data import (  # noqa: E402
    abs_census,
    bocsar_crime,
    common,
    nsw_hazards,
    nsw_planning_da,
    nsw_zoning,
)

SOURCES = {
    "nsw_planning_da": nsw_planning_da.fetch,
    "nsw_zoning": nsw_zoning.fetch,
    "nsw_hazards": nsw_hazards.fetch,
    "bocsar_crime": bocsar_crime.fetch,
    "abs_census": abs_census.fetch,
    "abs_erp": abs_census.fetch,
}


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Fetch NSW land/planning/stats data.")
    p.add_argument(
        "--config", type=Path, default=None, help="Path to land_data_config.json"
    )
    p.add_argument("--out", type=Path, default=None, help="Output directory")
    p.add_argument(
        "--only", nargs="+", choices=list(SOURCES), help="Run only these sources"
    )
    p.add_argument(
        "--list", action="store_true", help="List available sources and exit"
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Show plan without network calls"
    )
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.list:
        print("Available sources:")
        for name in SOURCES:
            print(f"  - {name}")
        return 0

    cfg = common.load_config(args.config)
    site = common.Site.from_config(cfg)
    http_cfg = cfg.get("http", {})
    sources_cfg = cfg.get("sources", {})

    out_dir = common.ensure_out_dir(args.out or common.DEFAULT_OUTPUT_DIR)

    selected = args.only or list(SOURCES)
    enabled = [
        name for name in selected if sources_cfg.get(name, {}).get("enabled", True)
    ]
    skipped = [n for n in selected if n not in enabled]

    common.log(f"Site: {site.address or '(address not set)'} | LGA: {site.lga_name}")
    common.log(f"Point: lat={site.lat}, lon={site.lon}")
    common.log(f"Output: {out_dir}")
    common.log(f"Sources to run: {', '.join(enabled) or '(none)'}")
    if skipped:
        common.log(f"Skipped (disabled): {', '.join(skipped)}")

    if args.dry_run:
        common.log("Dry run — no network calls made.")
        return 0

    summaries = []
    for name in enabled:
        common.log(f"=== {name} ===")
        try:
            summary = SOURCES[name](sources_cfg.get(name, {}), site, http_cfg, out_dir)
        except Exception as e:  # noqa: BLE001 - keep the pipeline alive
            summary = {"source": name, "ok": False, "error": f"{type(e).__name__}: {e}"}
            common.log(f"!! {name} crashed: {e}")
        summaries.append(summary)

    run_report = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "site": {
            "address": site.address,
            "lga_name": site.lga_name,
            "lat": site.lat,
            "lon": site.lon,
        },
        "results": summaries,
    }
    common.write_json(out_dir, "land_data_run_report", run_report)

    print("\nSummary:")
    for s in summaries:
        flag = "OK " if s.get("ok") else "ERR"
        extra = s.get("error", "")
        count = s.get("record_count", s.get("feature_count", ""))
        print(
            f"  [{flag}] {s['source']:<18} {('n=' + str(count)) if count != '' else '':<10} {extra}"
        )

    return 0 if all(s.get("ok") for s in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
