import xml.etree.ElementTree as ET
import json
import re

tree = ET.parse(r'c:\appRepo\react-map-template\public\practices.kml')
root = tree.getroot()
ns = {'kml': 'http://www.opengis.net/kml/2.2'}

folder = root.find('.//kml:Folder', ns)
placemarks = folder.findall('kml:Placemark', ns)
print('Total placemarks:', len(placemarks))

# Parse description HTML to extract field values
def parse_desc(desc):
    if not desc:
        return {}
    fields = {}
    # Each field is "FIELDNAME: value<br>"
    pattern = r'([A-Z_0-9]+):\s*(.*?)(?=<br>|$)'
    for m in re.finditer(pattern, desc):
        k = m.group(1).strip()
        v = m.group(2).strip()
        if v:
            fields[k] = v
    return fields

features = []
for pm in placemarks:
    name = pm.find('kml:name', ns)
    desc = pm.find('kml:description', ns)
    coords = pm.find('.//kml:coordinates', ns)

    pname = name.text.strip() if name is not None else ''
    fields = parse_desc(desc.text if desc is not None else '')

    # Get coordinates
    lng, lat = None, None
    if coords is not None:
        parts = coords.text.strip().split(',')
        if len(parts) >= 2:
            try:
                lng = float(parts[0])
                lat = float(parts[1])
            except:
                pass

    # Fallback to LATITUDE/LONGITUDE in fields
    if lat is None:
        try:
            lat = float(fields.get('LATITUDE', ''))
            lng = float(fields.get('LONGITUDE', ''))
        except:
            pass

    if lat is None or lng is None:
        continue

    state = fields.get('STATE', '').strip()
    postcode = str(fields.get('POSTCODE', '')).replace('.0','').strip()
    phone_raw = fields.get('SERVICE_PH', '')
    # Extract first phone number
    phone_match = re.search(r'[\d\s\(\)]{8,}', phone_raw)
    phone = phone_match.group(0).strip() if phone_match else phone_raw[:30]

    bulk = fields.get('FREE_PROVI', '')
    bulk_billing = 'bulk' in bulk.lower()
    telehealth = fields.get('TELEHEALTH', '').lower() == 'true'
    website = fields.get('WEB_SITE', '').strip()
    email = fields.get('EMAIL', '').strip()
    hours = fields.get('SERVICE_AV', '').strip()
    address = fields.get('ADDRESS', '').strip()
    suburb = fields.get('SUBURB', '').strip()
    service_comment = fields.get('SERVICE_CO', '').strip()[:200]
    facilities = fields.get('SITE_FACIL', '').strip()

    feature = {
        'type': 'Feature',
        'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
        'properties': {
            'name':          pname,
            'address':       address,
            'suburb':        suburb,
            'state':         state,
            'postcode':      postcode,
            'phone':         phone,
            'email':         email,
            'website':       website,
            'bulk_billing':  bulk_billing,
            'telehealth':    telehealth,
            'hours':         hours,
            'comment':       service_comment,
            'facilities':    facilities,
        }
    }
    features.append(feature)

geojson = {'type': 'FeatureCollection', 'features': features}
out = r'c:\appRepo\react-map-template\public\practices.geojson'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(geojson, f, ensure_ascii=False)

print('GeoJSON features written:', len(features))
print('Output:', out)

# State summary
from collections import Counter
states = Counter(f['properties']['state'] for f in features)
for s, c in sorted(states.items()):
    print(f'  {s}: {c}')

# Sample
print('\nSample:')
for f in features[:2]:
    p = f['properties']
    print(' ', p['name'], '|', p['suburb'], p['state'], '|', p['phone'], '| bulk:', p['bulk_billing'], '| lat/lng:', f['geometry']['coordinates'])
