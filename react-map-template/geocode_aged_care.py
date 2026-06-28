"""
Geocode aged care facilities from KML via Nominatim (OSM).
Runs at 1 request/sec to respect rate limit.
"""
import xml.etree.ElementTree as ET
import json, re, time, urllib.request, urllib.parse

KML  = r'c:\appRepo\react-map-template\public\aged-care.kml'
OUT  = r'c:\appRepo\react-map-template\public\aged-care.geojson'

tree = ET.parse(KML)
root = tree.getroot()
ns   = {'kml': 'http://www.opengis.net/kml/2.2'}
placemarks = root.findall('.//kml:Placemark', ns)
print(f'Total placemarks: {len(placemarks)}')

def parse_desc(text):
    fields = {}
    if not text:
        return fields
    for part in text.split('<br>'):
        if ': ' in part:
            k, _, v = part.partition(': ')
            fields[k.strip()] = v.strip()
    return fields

def geocode(address):
    q = urllib.parse.quote(address)
    url = f'https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1&countrycodes=au'
    req = urllib.request.Request(url, headers={'User-Agent': 'AgedCareGeocoder/1.0 (research-project)'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        if data:
            return float(data[0]['lon']), float(data[0]['lat'])
    except Exception as e:
        pass
    return None, None

features = []
skipped  = 0

for i, pm in enumerate(placemarks):
    name_el = pm.find('kml:name', ns)
    desc_el = pm.find('kml:description', ns)
    pname   = name_el.text.strip() if name_el is not None and name_el.text else ''
    fields  = parse_desc(desc_el.text if desc_el is not None else '')

    # Try existing coordinates first (Point in ExtendedData)
    coord_str = fields.get('Location: Coordinates', '')
    m = re.search(r'Point\s*\(([0-9.\-]+)\s+([0-9.\-]+)\)', coord_str)
    if m:
        lng, lat = float(m.group(1)), float(m.group(2))
    else:
        addr = fields.get('Address', '').strip()
        if not addr:
            print(f'  Skip {i}: no address for {pname[:40]}')
            skipped += 1
            continue
        time.sleep(1.1)  # Nominatim: 1 req/sec
        lng, lat = geocode(addr)
        if lng is None:
            print(f'  FAIL {i}: {addr[:50]}')
            skipped += 1
            continue
        print(f'  {i+1}/{len(placemarks)} OK: {pname[:35]:<35} {lat:.4f},{lng:.4f}')

    title    = fields.get('Title', pname).strip()
    state    = fields.get('Location: State', '').strip()
    suburb   = fields.get('Location: City', '').strip()
    postcode = str(fields.get('Location: Postal Code', '')).replace('.0','').strip()
    phone    = fields.get('Business Phone', '').strip()
    email    = fields.get('E-mail Address', '').strip()
    website  = fields.get('Web Page', '').strip()
    notes    = fields.get('Notes', '').strip()
    street   = fields.get('Location: Street', '').strip()
    loc_name = fields.get('Location: Name', '').strip()

    # Derive state/suburb/postcode from raw address if not in Location fields
    if not state:
        addr_full = fields.get('Address', '')
        m2 = re.search(r',\s*([A-Z]{2,3}),\s*(\d{4})', addr_full)
        if m2:
            state    = m2.group(1)
            postcode = m2.group(2)
        m3 = re.search(r',\s*([A-Z][A-Z ]+),\s*[A-Z]{2,3},', addr_full)
        if m3 and not suburb:
            suburb = m3.group(1).strip()

    address = street
    if suburb:   address += (', ' if address else '') + suburb
    if state:    address += (', ' if address else '') + state
    if postcode: address += (' '  if address else '') + postcode

    features.append({
        'type': 'Feature',
        'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
        'properties': {
            'name':      title or pname,
            'full_name': loc_name or pname,
            'address':   address or fields.get('Address','')[:120],
            'suburb':    suburb,
            'state':     state,
            'postcode':  postcode,
            'phone':     phone,
            'email':     email,
            'website':   website,
            'notes':     notes[:200] if notes else '',
            'type':      'aged_care',
        }
    })

geojson = {'type': 'FeatureCollection', 'features': features}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print(f'\nSaved {len(features)} features, skipped {skipped}')
from collections import Counter
for s, c in sorted(Counter(f['properties']['state'] for f in features).items()):
    print(f'  {s}: {c}')
