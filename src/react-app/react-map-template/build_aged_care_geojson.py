"""
Build aged-care.geojson from the GEN AIHW Aged Care Service List 2025.
Keeps: name, address/suburb/state/postcode, lat/lng, provider name,
       care_type, phn_name, and a My Aged Care search URL.
"""
import openpyxl, json, urllib.parse
from collections import Counter

SRC = r'c:\appRepo\extDataSets\aged-care-service-list-2025.xlsx'
OUT = r'c:\appRepo\react-map-template\public\aged-care.geojson'

wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
ws = wb.active

# Find header row (row 3)
rows = ws.iter_rows(values_only=True)
next(rows)  # title row
next(rows)  # blank row
headers = list(next(rows))
print('Columns:', headers)

COL = {h: i for i, h in enumerate(headers) if h}

features = []
skipped  = 0

for row in rows:
    name    = row[COL['Service Name']]
    lat     = row[COL['Latitude']]
    lng     = row[COL['Longitude']]
    if not name or lat is None or lng is None:
        skipped += 1
        continue

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        skipped += 1
        continue

    address  = str(row[COL['Physical Address']] or '').strip()
    suburb   = str(row[COL['Physical Suburb']] or '').strip()
    state    = str(row[COL['Physical State']] or '').strip()
    postcode = str(row[COL['Physical Post Code']] or '').replace('.0', '').strip()
    provider = str(row[COL['Provider Name']] or '').strip()
    care_type= str(row[COL['Care Type']] or '').strip()
    phn_name = str(row[COL['2017 PHN Name']] or '').strip()

    # Build a My Aged Care search URL (no direct per-facility URL in the dataset)
    search_q = urllib.parse.quote(f"{name} {suburb} {state}")
    url = f"https://www.myagedcare.gov.au/find-a-provider#!%7B%22keyword%22%3A%22{urllib.parse.quote(name)}%22%7D"

    full_address = ', '.join(filter(None, [address, suburb, state, postcode]))

    features.append({
        'type': 'Feature',
        'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
        'properties': {
            'name':      name,
            'provider':  provider,
            'address':   full_address,
            'suburb':    suburb,
            'state':     state,
            'postcode':  postcode,
            'care_type': care_type,
            'phn_name':  phn_name,
            'url':       url,
            'type':      'aged_care',
        }
    })

geojson = {'type': 'FeatureCollection', 'features': features}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print(f'\nSaved {len(features)} features, skipped {skipped}')
print('\nBy state:')
for s, c in sorted(Counter(f['properties']['state'] for f in features).items()):
    print(f'  {s}: {c}')
print('\nBy care type:')
for t, c in sorted(Counter(f['properties']['care_type'] for f in features).items(), key=lambda x: -x[1]):
    print(f'  {t}: {c}')
