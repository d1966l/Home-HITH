import xml.etree.ElementTree as ET
import json

tree = ET.parse(r'c:\appRepo\react-map-template\public\practices.kml')
root = tree.getroot()
ns = {'kml': 'http://www.opengis.net/kml/2.2'}

folders = root.findall('.//kml:Folder', ns)
print('Folders:', len(folders))
for f in folders[:10]:
    name = f.find('kml:name', ns)
    places = f.findall('kml:Placemark', ns)
    fname = name.text if name is not None else '?'
    print('  Folder:', fname, '  Placemarks:', len(places))

# Sample first placemark
pm = root.find('.//kml:Placemark', ns)
if pm:
    print()
    print('=== Sample Placemark ===')
    for child in pm:
        tag = child.tag.split('}')[-1]
        print('  tag:', tag, '|', repr(child.text))
        for sub in child:
            stag = sub.tag.split('}')[-1]
            print('    sub:', stag, '|', repr(sub.text))
            for s2 in sub:
                s2tag = s2.tag.split('}')[-1]
                print('      s2:', s2tag, '|', repr(s2.text))
