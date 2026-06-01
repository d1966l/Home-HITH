import { useEffect, useRef, useState, useMemo } from 'react'
import {
  MapContainer, TileLayer, GeoJSON, useMap, Marker, Popup,
} from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix Leaflet default icon paths broken by bundlers
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
  iconUrl:       new URL('leaflet/dist/images/marker-icon.png',    import.meta.url).href,
  shadowUrl:     new URL('leaflet/dist/images/marker-shadow.png',  import.meta.url).href,
})

const STATE_CODE = {
  'New South Wales':              'NSW',
  'Victoria':                     'VIC',
  'Queensland':                   'QLD',
  'South Australia':              'SA',
  'Western Australia':            'WA',
  'Tasmania':                     'TAS',
  'Northern Territory':           'NT',
  'Australian Capital Territory': 'ACT',
}

const METRIC_LABELS = {
  total_gps:     'Total GPs',
  total_gpfte:   'GP FTE',
  vr_gpfte:      'VR GP FTE',
  nonvr_gpfte:   'Non-VR GP FTE',
  trainee_gpfte: 'GP Trainee FTE',
}

const MAP_TYPE_NAMES = {
  medical:     'Medical Practices',
  aged_care:   'Aged Care Facilities',
  hospitals:   'Hospitals',
  specialists: 'Specialists',
}

const DATA_URLS = {
  medical:     '/practices.geojson',
  aged_care:   '/aged-care.geojson',
  hospitals:   '/hospitals.geojson',
  specialists: null,
}

const FACILITY_LABELS = {
  medical:     { plural: 'practices',  badge: '📍' },
  aged_care:   { plural: 'facilities', badge: '🏡' },
  hospitals:   { plural: 'hospitals',  badge: '🏨' },
  specialists: { plural: 'specialists',badge: '🩺' },
}

function normalizeState(s) {
  return s ? s.toUpperCase() : ''
}

function lerp(a, b, t) { return Math.round(a + (b - a) * t) }

function gpColor(value, min, max) {
  if (value == null) return '#1e3a5f'
  const t = Math.pow((value - min) / (max - min || 1), 0.5)
  return `rgb(${lerp(186,29,t)},${lerp(230,78,t)},${lerp(255,216,t)})`
}

// Fly map to bounds when selectedState changes
function FlyToState({ geoData, selectedState }) {
  const map = useMap()
  useEffect(() => {
    if (!selectedState || !geoData) return
    const feature = geoData.features.find(
      f => STATE_CODE[f.properties.STATE_NAME] === selectedState
    )
    if (!feature) return
    const layer = L.geoJSON(feature)
    const bounds = layer.getBounds()
    if (bounds.isValid()) map.flyToBounds(bounds, { padding: [30, 30], duration: 0.8 })
  }, [selectedState, geoData, map])

  useEffect(() => {
    if (!selectedState) {
      map.flyTo([-27, 134], 4, { duration: 0.8 })
    }
  }, [selectedState, map])

  return null
}

// Custom marker icon — colour by map type (or state for medical)
const STATE_COLORS = {
  NSW: '#097138', VIC: '#1A237E', QLD: '#795548', SA: '#01579B',
  WA: '#F57C00', TAS: '#880E4F', NT: '#7CB342', ACT: '#9C27B0',
}
const TYPE_COLORS = {
  aged_care:   '#10b981',
  hospitals:   '#f59e0b',
  specialists: '#a78bfa',
}

function makeMarkerIcon(state, mapType) {
  const color = TYPE_COLORS[mapType] || STATE_COLORS[state] || '#e63946'
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="32" viewBox="0 0 22 32">
    <path d="M11 0C4.9 0 0 4.9 0 11c0 7.7 11 21 11 21s11-13.3 11-21C22 4.9 17.1 0 11 0z"
      fill="${color}" stroke="white" stroke-width="1.5"/>
    <circle cx="11" cy="11" r="4.5" fill="white"/>
  </svg>`
  return L.divIcon({ html: svg, className: '', iconSize: [22, 32], iconAnchor: [11, 32], popupAnchor: [0, -34] })
}

// ── Popup components ──────────────────────────────────────────
function MedicalPopup({ p }) {
  return (
    <>
      <div className="popup-name">{p.name}</div>
      <div className="popup-address">
        📍 {p.address}{p.suburb ? `, ${p.suburb}` : ''} {p.state} {p.postcode}
      </div>
      {p.phone && (
        <div className="popup-row">📞 <a href={`tel:${p.phone.replace(/\s/g,'')}`}>{p.phone}</a></div>
      )}
      {p.email && (
        <div className="popup-row">✉️ <a href={`mailto:${p.email}`}>{p.email}</a></div>
      )}
      {p.website && p.website.startsWith('http') && (
        <div className="popup-row">🌐 <a href={p.website} target="_blank" rel="noreferrer">{p.website.replace(/^https?:\/\//,'')}</a></div>
      )}
      <div className="popup-tags">
        {p.bulk_billing && <span className="tag-bulk">Bulk Billing</span>}
        {p.telehealth   && <span className="tag-tele">Telehealth</span>}
        <span className="tag-state">{p.state}</span>
      </div>
      {p.hours && (
        <details className="popup-hours">
          <summary>Hours</summary>
          <pre>{p.hours}</pre>
        </details>
      )}
    </>
  )
}

function AgedCarePopup({ p }) {
  return (
    <>
      <div className="popup-name">{p.name}</div>
      {p.provider && p.provider !== p.name && (
        <div style={{fontSize:'0.74rem',color:'#94a3b8',marginBottom:4}}>{p.provider}</div>
      )}
      {p.address && <div className="popup-address">📍 {p.address}</div>}
      {p.url && (
        <div className="popup-row">🌐 <a href={p.url} target="_blank" rel="noreferrer">My Aged Care</a></div>
      )}
      <div className="popup-tags">
        <span className="tag-state">{p.state}</span>
        {p.care_type && <span className="tag-tele" style={{background:'#14532d',color:'#4ade80',borderColor:'#166534',border:'1px solid'}}>{p.care_type}</span>}
      </div>
      {p.phn_name && <div style={{fontSize:'0.74rem',color:'#94a3b8',marginTop:4}}>PHN: {p.phn_name}</div>}
    </>
  )
}

function HospitalPopup({ p }) {
  return (
    <>
      <div className="popup-name">{p.name}</div>
      <div className="popup-address">📍 {p.state}</div>
      <div className="popup-tags">
        <span className={p.is_public ? 'tag-bulk' : 'tag-tele'}>
          {p.is_public ? '🏛 Public' : '🏢 Private'}
        </span>
        <span className="tag-state">{p.state}</span>
      </div>
      {p.phn_name && <div className="popup-row" style={{marginTop:4}}>PHN: {p.phn_name}</div>}
    </>
  )
}

// ─────────────────────────────────────────────────────────────
export default function AustraliaMap({
  stateData, metric, year, selectedState, onStateSelect, mapType = 'medical',
}) {
  const [geoData,      setGeoData]      = useState(null)
  const [facilityData, setFacilityData] = useState(null)
  const geoJsonLayerRef = useRef(null)

  // Load state boundaries once
  useEffect(() => {
    fetch('/australia-states.geojson').then(r => r.json()).then(setGeoData)
  }, [])

  // Load facility data whenever mapType changes
  useEffect(() => {
    setFacilityData(null)
    const url = DATA_URLS[mapType]
    if (url) {
      fetch(url)
        .then(r => r.json())
        .then(setFacilityData)
        .catch(() => setFacilityData(null))
    }
  }, [mapType])

  // Per-state counts for choropleth on non-medical layers
  const stateCounts = useMemo(() => {
    if (mapType === 'medical' || !facilityData) return {}
    const counts = {}
    facilityData.features.forEach(f => {
      const s = normalizeState(f.properties.state || '')
      if (s) counts[s] = (counts[s] || 0) + 1
    })
    return counts
  }, [facilityData, mapType])

  // Colour scale
  const values = geoData
    ? geoData.features
        .map(f => {
          const code = STATE_CODE[f.properties.STATE_NAME]
          return mapType === 'medical'
            ? stateData[code]?.[metric]?.[year]
            : stateCounts[code]
        })
        .filter(v => v != null)
    : []
  const minVal = values.length ? Math.min(...values) : 0
  const maxVal = values.length ? Math.max(...values) : 1

  function stateStyle(feature) {
    const code = STATE_CODE[feature.properties.STATE_NAME]
    const val  = mapType === 'medical'
      ? stateData[code]?.[metric]?.[year]
      : stateCounts[code]
    const sel  = selectedState === code
    return {
      fillColor:   gpColor(val, minVal, maxVal),
      fillOpacity: sel ? 0.65 : 0.48,
      color:       sel ? '#f59e0b' : '#0f172a',
      weight:      sel ? 2.5 : 0.7,
    }
  }

  function onEachState(feature, layer) {
    const code  = STATE_CODE[feature.properties.STATE_NAME]
    const val   = mapType === 'medical' ? stateData[code]?.[metric]?.[year] : stateCounts[code]
    const label = mapType === 'medical'
      ? (METRIC_LABELS[metric] || metric)
      : (FACILITY_LABELS[mapType]?.plural || 'facilities')
    layer.bindTooltip(
      `<div class="state-tooltip">
        <strong>${feature.properties.STATE_NAME}</strong><br/>
        ${label}: <b>${val != null ? val.toLocaleString() : 'N/A'}</b>
        <br/><span class="tt-hint">Click to inspect</span>
      </div>`,
      { sticky: true, className: 'leaflet-state-tooltip' }
    )
    layer.on({
      click:     () => onStateSelect(selectedState === code ? null : code),
      mouseover: e  => { e.target.setStyle({ fillOpacity: 0.75, weight: 2 }); e.target.bringToFront() },
      mouseout:  e  => { if (geoJsonLayerRef.current) geoJsonLayerRef.current.resetStyle(e.target) },
    })
  }

  // Filter facilities to selected state
  const visibleFacilities = facilityData
    ? facilityData.features.filter(f =>
        !selectedState || normalizeState(f.properties.state) === selectedState
      )
    : []

  const metricLabel = METRIC_LABELS[metric] || metric
  const facLabel    = FACILITY_LABELS[mapType] || FACILITY_LABELS.medical

  return (
    <div className="map-wrapper">
      <div className="map-heading">
        <h2>
          {mapType === 'medical'
            ? `${metricLabel} — Australia ${year}`
            : `${MAP_TYPE_NAMES[mapType]} — Australia`}
        </h2>
        {selectedState && (
          <button className="clear-state-btn" onClick={() => onStateSelect(null)}>
            ✕ {selectedState}
          </button>
        )}
      </div>

      <MapContainer
        center={[-27, 134]}
        zoom={4}
        minZoom={3}
        maxZoom={16}
        style={{ height: '540px', width: '100%', borderRadius: '10px' }}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />

        {geoData && (
          <GeoJSON
            key={`${metric}-${year}-${selectedState}-${mapType}`}
            ref={geoJsonLayerRef}
            data={geoData}
            style={stateStyle}
            onEachFeature={onEachState}
          />
        )}

        {facilityData && mapType !== 'specialists' && (
          <MarkerClusterGroup
            chunkedLoading
            maxClusterRadius={50}
            showCoverageOnHover={false}
            iconCreateFunction={cluster => {
              const count = cluster.getChildCount()
              const size  = count > 100 ? 44 : count > 20 ? 36 : 28
              return L.divIcon({
                html: `<div class="cluster-icon" style="width:${size}px;height:${size}px;line-height:${size}px">${count}</div>`,
                className: '',
                iconSize: [size, size],
              })
            }}
          >
            {visibleFacilities.map((f, i) => {
              const p   = f.properties
              const pos = [f.geometry.coordinates[1], f.geometry.coordinates[0]]
              return (
                <Marker
                  key={`${mapType}-${i}`}
                  position={pos}
                  icon={makeMarkerIcon(normalizeState(p.state), mapType)}
                >
                  <Popup maxWidth={300} className="practice-popup">
                    <div className="popup-content">
                      {mapType === 'medical'   && <MedicalPopup   p={p} />}
                      {mapType === 'aged_care' && <AgedCarePopup  p={p} />}
                      {mapType === 'hospitals' && <HospitalPopup  p={p} />}
                    </div>
                  </Popup>
                </Marker>
              )
            })}
          </MarkerClusterGroup>
        )}

        {geoData && <FlyToState geoData={geoData} selectedState={selectedState} />}
      </MapContainer>

      {/* Colour legend */}
      <div className="map-legend">
        <span className="legend-low">{minVal.toLocaleString()}</span>
        <div className="legend-bar" />
        <span className="legend-high">{maxVal.toLocaleString()}</span>
        <span className="legend-label">
          {mapType === 'medical' ? metricLabel : facLabel.plural}
        </span>
      </div>

      {/* Facility count badge */}
      {mapType !== 'specialists' && facilityData && (
        <div className="practice-count-badge">
          {facLabel.badge} {visibleFacilities.length.toLocaleString()} {facLabel.plural} shown
          {selectedState ? ` in ${selectedState}` : ' nationally'}
        </div>
      )}
      {mapType === 'specialists' && (
        <div className="practice-count-badge" style={{background:'#1e1b4b',color:'#a78bfa',borderColor:'#4338ca'}}>
          🩺 Specialist data — coming soon
        </div>
      )}
    </div>
  )
}
