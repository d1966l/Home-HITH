"""
refresh-map-data.py
───────────────────
Refreshes map GeoJSON files from their live public sources.

Data sources
  hospitals.geojson  →  AIHW MyHospitals API  (always current)
  aged-care.geojson  →  GEN AIHW Service List  (annual XLSX, Oct release)
  practices.geojson  →  Google My Maps KML     (MANUAL – see note below)

Usage
  python refresh-map-data.py            # refresh all
  python refresh-map-data.py hospitals  # single source
  python refresh-map-data.py aged_care

GP practices note
  Google My Maps has no public API.  To refresh:
    1. Open https://www.google.com/maps/d/edit?mid=1FttVohP8Gh-JWl1KWaX_rlUqaI6PpN0
    2. ⋮  →  Export to KML  →  download .kml
    3. Run:  python refresh-map-data.py practices --kml path/to/file.kml
"""

import sys, json, urllib.request, urllib.parse, openpyxl, re, os, tempfile, shutil
from pathlib import Path
from collections import Counter

PUBLIC = Path(__file__).parent / "public"
CACHE  = Path(__file__).parent / ".data-cache"
CACHE.mkdir(exist_ok=True)

# ── Aged care URL – update this path each October when GEN publishes new data ─
# Pattern: https://www.gen-agedcaredata.gov.au/resources/access-data/{YEAR}/{MONTH}/aged-care-service-list-30-june-{YEAR}
AGED_CARE_PAGE = "https://www.gen-agedcaredata.gov.au/resources/access-data/2025/october/aged-care-service-list-30-june-2025"
AGED_CARE_XLSX = "https://www.gen-agedcaredata.gov.au/getmedia/2599a590-3c5f-4227-aac3-f0a3a8aa84e4/Service-List-2025-Australia_300126"

HOSPITALS_API  = "https://myhospitalsapi.aihw.gov.au/api/v0/retired-myhospitals-api/hospitals"


# ══════════════════════════════════════════════════════════════════════════════
def refresh_hospitals():
    print("\n── Hospitals ─────────────────────────────")
    req = urllib.request.Request(
        HOSPITALS_API,
        headers={"User-Agent": "HealthMapRefresh/1.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())

    features = []
    skipped  = 0
    for h in data:
        if h.get("isclosed"):
            skipped += 1
            continue
        lat = h.get("latitude")
        lng = h.get("longitude")
        if lat is None or lng is None:
            skipped += 1
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
            "properties": {
                "name":      h.get("name", ""),
                "state":     (h.get("state") or "").upper(),
                "phn_name":  h.get("phnname", ""),
                "phn_code":  h.get("phncode", ""),
                "is_public": bool(h.get("ispublic")),
                "code":      h.get("code", ""),
                "type":      "hospital",
            }
        })

    _write_geojson(PUBLIC / "hospitals.geojson", features)
    print(f"  Saved {len(features)} hospitals ({skipped} skipped/closed)")
    for s, c in sorted(Counter(f["properties"]["state"] for f in features).items()):
        print(f"    {s}: {c}")


# ══════════════════════════════════════════════════════════════════════════════
def refresh_aged_care(xlsx_path=None):
    print("\n── Aged Care ─────────────────────────────")

    if xlsx_path:
        src = Path(xlsx_path)
        print(f"  Using local file: {src}")
    else:
        # Try to find the XLSX download link from the GEN page
        xlsx_url = _find_aged_care_xlsx_url() or AGED_CARE_XLSX
        print(f"  Downloading: {xlsx_url}")
        src = CACHE / "aged-care-service-list.xlsx"
        req = urllib.request.Request(
            xlsx_url, headers={"User-Agent": "HealthMapRefresh/1.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            src.write_bytes(r.read())
        print(f"  Downloaded {src.stat().st_size:,} bytes")

    wb = openpyxl.load_workbook(str(src), read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    next(rows); next(rows)                  # skip title + blank
    headers = list(next(rows))
    COL = {h: i for i, h in enumerate(headers) if h}

    features = []
    skipped  = 0
    for row in rows:
        name = row[COL["Service Name"]]
        lat  = row[COL["Latitude"]]
        lng  = row[COL["Longitude"]]
        if not name or lat is None or lng is None:
            skipped += 1
            continue
        try:
            lat, lng = float(lat), float(lng)
        except (TypeError, ValueError):
            skipped += 1
            continue

        address  = str(row[COL["Physical Address"]]      or "").strip()
        suburb   = str(row[COL["Physical Suburb"]]       or "").strip()
        state    = str(row[COL["Physical State"]]        or "").strip()
        postcode = str(row[COL["Physical Post Code"]]    or "").replace(".0","").strip()
        provider = str(row[COL["Provider Name"]]         or "").strip()
        care_type= str(row[COL["Care Type"]]             or "").strip()
        phn_name = str(row[COL["2017 PHN Name"]]         or "").strip()

        search_name = urllib.parse.quote(name)
        url = f"https://www.myagedcare.gov.au/find-a-provider#!%7B%22keyword%22%3A%22{search_name}%22%7D"

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": {
                "name":      name,
                "provider":  provider,
                "address":   ", ".join(filter(None, [address, suburb, state, postcode])),
                "suburb":    suburb,
                "state":     state,
                "postcode":  postcode,
                "care_type": care_type,
                "phn_name":  phn_name,
                "url":       url,
                "type":      "aged_care",
            }
        })

    _write_geojson(PUBLIC / "aged-care.geojson", features)
    print(f"  Saved {len(features)} facilities ({skipped} skipped)")
    for s, c in sorted(Counter(f["properties"]["state"] for f in features).items()):
        print(f"    {s}: {c}")


# ══════════════════════════════════════════════════════════════════════════════
def refresh_practices(kml_path):
    """Convert a Google My Maps KML export to practices.geojson."""
    import xml.etree.ElementTree as ET
    print(f"\n── GP Practices (KML: {kml_path}) ────────")
    tree = ET.parse(kml_path)
    root = tree.getroot()
    ns   = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//kml:Placemark", ns)
    print(f"  Found {len(placemarks)} placemarks")

    features = []
    for pm in placemarks:
        name_el  = pm.find("kml:name", ns)
        coord_el = pm.find(".//kml:coordinates", ns)
        desc_el  = pm.find("kml:description", ns)
        name     = name_el.text.strip() if name_el is not None and name_el.text else ""
        if not name or coord_el is None:
            continue
        coords = coord_el.text.strip().split(",")
        if len(coords) < 2:
            continue
        lng, lat = float(coords[0]), float(coords[1])

        fields = {}
        if desc_el is not None and desc_el.text:
            for part in desc_el.text.split("<br>"):
                if ": " in part:
                    k, _, v = part.partition(": ")
                    fields[k.strip()] = v.strip()

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": {
                "name":     name,
                "address":  fields.get("Address", ""),
                "phone":    fields.get("Phone", ""),
                "type":     "practice",
            }
        })

    _write_geojson(PUBLIC / "practices.geojson", features)
    print(f"  Saved {len(features)} practices")


# ══════════════════════════════════════════════════════════════════════════════
def _find_aged_care_xlsx_url():
    """Scrape the GEN page to find the current national XLSX download URL."""
    try:
        req = urllib.request.Request(
            AGED_CARE_PAGE, headers={"User-Agent": "HealthMapRefresh/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
        # Find a .xlsx link for the Australia service list
        m = re.search(r'href="(https://www\.gen-agedcaredata\.gov\.au/getmedia/[^"]+)"[^>]*>Australia service list[^<]*\(XLSX', html)
        if m:
            print(f"  Found XLSX URL on GEN page: {m.group(1)[:80]}...")
            return m.group(1)
    except Exception as e:
        print(f"  Could not scrape GEN page ({e}), using cached URL")
    return None


def _write_geojson(path, features):
    geojson = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written → {path}  ({path.stat().st_size:,} bytes)")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    targets = sys.argv[1:]
    kml_arg = None
    if "--kml" in targets:
        idx = targets.index("--kml")
        kml_arg = targets[idx + 1]
        targets = [t for t in targets if t not in ("--kml", kml_arg)]
    if not targets:
        targets = ["hospitals", "aged_care"]

    if "hospitals" in targets:
        refresh_hospitals()
    if "aged_care" in targets:
        refresh_aged_care()
    if "practices" in targets:
        if not kml_arg:
            print("\nGP practices refresh requires --kml <path>")
            print("  Export KML from Google My Maps then run:")
            print("  python refresh-map-data.py practices --kml path/to/export.kml")
        else:
            refresh_practices(kml_arg)

    print("\nDone.")
