import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './MapView.scss'

// Fix default leaflet marker icon paths broken by Vite bundling
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
})

const STATUS_COLOR = {
  online: '#00ffb3',
  idle: '#f0c040',
  visible: '#a880ff',
}

function makeIcon(status) {
  const color = STATUS_COLOR[status] ?? '#888'
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">
      <ellipse cx="14" cy="34" rx="5" ry="2" fill="rgba(0,0,0,0.3)"/>
      <path d="M14 0C8.48 0 4 4.48 4 10c0 7.5 10 26 10 26S24 17.5 24 10C24 4.48 19.52 0 14 0z"
            fill="${color}" stroke="#0a0a1a" stroke-width="1.5"/>
      <circle cx="14" cy="10" r="4" fill="#0a0a1a" opacity="0.6"/>
    </svg>`
  return L.divIcon({
    html: svg,
    className: '',
    iconSize: [28, 36],
    iconAnchor: [14, 36],
    popupAnchor: [0, -36],
  })
}

// Fly to selected marker when selection changes
function FlyTo({ item }) {
  const map = useMap()
  useEffect(() => {
    if (item) map.flyTo([item.lat, item.lng], 17, { duration: 0.8 })
  }, [item, map])
  return null
}

export default function MapView({ items, selected, onSelect }) {
  const center = [-33.8688, 151.2093]

  return (
    <div className="map-view">
      <MapContainer
        center={center}
        zoom={16}
        className="map-view__leaflet"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FlyTo item={selected} />
        {items.map(item => (
          <Marker
            key={item.id}
            position={[item.lat, item.lng]}
            icon={makeIcon(item.status)}
            eventHandlers={{ click: () => onSelect(selected?.id === item.id ? null : item) }}
          >
            <Popup>
              <div className="map-popup">
                <strong>{item.name}</strong>
                <span>{item.type}</span>
                {item.address && <code>{item.address}</code>}
                <p>{item.description}</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
