"""Write updated React component files for map type selector feature."""
import pathlib

BASE = pathlib.Path(r'c:\appRepo\react-map-template\src')

# ─────────────────────────────────────────────────────────────
# App.jsx
# ─────────────────────────────────────────────────────────────
APP_JSX = r"""import { useState } from 'react'
import AustraliaMap  from './components/AustraliaMap'
import StatsPanel    from './components/StatsPanel'
import NationalStats from './components/NationalStats'
import gpData        from './gp-data.json'
import './App.css'

const METRICS = [
  { value: 'total_gps',     label: 'Total GPs' },
  { value: 'total_gpfte',   label: 'GP FTE (Full-Time Equiv.)' },
  { value: 'vr_gpfte',      label: 'VR GP FTE' },
  { value: 'nonvr_gpfte',   label: 'Non-VR GP FTE' },
  { value: 'trainee_gpfte', label: 'GP Trainee FTE' },
]

const MAP_TYPES = [
  { id: 'medical',     label: 'Medical Practice', icon: '🏥', color: '#3b82f6' },
  { id: 'aged_care',   label: 'Aged Care',         icon: '🏡', color: '#10b981' },
  { id: 'hospitals',   label: 'Hospitals',         icon: '🏨', color: '#f59e0b' },
  { id: 'specialists', label: 'Specialists',       icon: '🩺', color: '#a78bfa', placeholder: true },
]

export default function App() {
  const [selectedYear,  setSelectedYear]  = useState('2025')
  const [selectedState, setSelectedState] = useState(null)
  const [metric,        setMetric]        = useState('total_gps')
  const [mapType,       setMapType]       = useState('medical')

  const handleMapTypeChange = (id) => {
    setMapType(id)
    setSelectedState(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <span className="header-icon">🏥</span>
          <div>
            <h1>Australian Primary Care Dashboard</h1>
            <p>Calendar Years 2020–2025 · Source: AIHW Primary Care GP Statistics Dataset</p>
          </div>
        </div>
        <div className="header-controls">
          {mapType === 'medical' && (
            <>
              <div className="control-group">
                <label>Select Year</label>
                <div className="year-pills">
                  {gpData.years.map(y => (
                    <button
                      key={y}
                      className={`year-pill${selectedYear === y ? ' active' : ''}`}
                      onClick={() => setSelectedYear(y)}
                    >{y}</button>
                  ))}
                </div>
              </div>
              <div className="control-group">
                <label>Metric</label>
                <select
                  className="metric-select"
                  value={metric}
                  onChange={e => setMetric(e.target.value)}
                >
                  {METRICS.map(m => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>
            </>
          )}
        </div>
      </header>

      {/* Map type selector */}
      <div className="map-type-bar">
        {MAP_TYPES.map(t => (
          <button
            key={t.id}
            className={`map-type-btn${mapType === t.id ? ' active' : ''}${t.placeholder ? ' placeholder' : ''}`}
            style={{ '--type-color': t.color }}
            onClick={() => handleMapTypeChange(t.id)}
          >
            <span className="type-icon">{t.icon}</span>
            <span className="type-label">{t.label}</span>
            {t.placeholder && <span className="type-pill">Soon</span>}
          </button>
        ))}
      </div>

      {mapType === 'medical' && (
        <NationalStats data={gpData.national} year={selectedYear} />
      )}

      <main className="app-main">
        <section className="map-section">
          <AustraliaMap
            stateData={gpData.states}
            metric={metric}
            year={selectedYear}
            selectedState={selectedState}
            onStateSelect={setSelectedState}
            mapType={mapType}
          />
        </section>
        <aside className="panel-section">
          <StatsPanel
            stateData={gpData.states}
            nationalData={gpData.national}
            selectedState={selectedState}
            year={selectedYear}
            years={gpData.years}
            mapType={mapType}
          />
        </aside>
      </main>

      <footer className="app-footer">
        <span>react-map-template · GP Dataset 2020–2025 · Built with React + Vite + react-leaflet + Recharts</span>
      </footer>
    </div>
  )
}
"""

# ─────────────────────────────────────────────────────────────
# AustraliaMap.jsx
# ─────────────────────────────────────────────────────────────
AUSTRALIA_MAP_JSX = r"""import { useEffect, useRef, useState, useMemo } from 'react'
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
      {p.full_name && p.full_name !== p.name && (
        <div style={{fontSize:'0.74rem',color:'#94a3b8',marginBottom:4}}>{p.full_name}</div>
      )}
      {p.address && <div className="popup-address">📍 {p.address}</div>}
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
        <span className="tag-state">{p.state}</span>
        <span className="tag-tele" style={{background:'#14532d',color:'#4ade80',borderColor:'#166534',border:'1px solid'}}>Aged Care</span>
      </div>
      {p.notes && <div style={{fontSize:'0.74rem',color:'#94a3b8',marginTop:4}}>{p.notes}</div>}
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
"""

# ─────────────────────────────────────────────────────────────
# StatsPanel.jsx
# ─────────────────────────────────────────────────────────────
STATS_PANEL_JSX = r"""import { useEffect, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

const STATE_FULL = {
  NSW: 'New South Wales', VIC: 'Victoria',    QLD: 'Queensland',
  SA:  'South Australia', WA:  'Western Australia',
  TAS: 'Tasmania',        NT:  'Northern Territory',
  ACT: 'Australian Capital Territory',
}
const YEARS = ['2020','2021','2022','2023','2024','2025']

function fmt(n) {
  if (n == null) return '—'
  return typeof n === 'number' ? n.toLocaleString() : n
}

function normalizeState(s) {
  return s ? s.toUpperCase() : ''
}

// ── Medical practice card ─────────────────────────────────────
function PracticeCard({ p }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`practice-card${open ? ' open' : ''}`} onClick={() => setOpen(o => !o)}>
      <div className="practice-header">
        <div className="practice-name">{p.name}</div>
        <span className="practice-toggle">{open ? '▲' : '▼'}</span>
      </div>
      <div className="practice-meta">
        <span className="practice-location">📍 {p.suburb} {p.postcode}</span>
        {p.phone && <span className="practice-phone">📞 {p.phone}</span>}
      </div>
      <div className="practice-tags">
        {p.bulk_billing && <span className="tag bulk-billing">Bulk Billing</span>}
        {p.telehealth   && <span className="tag telehealth">Telehealth</span>}
        <span className="tag state-tag">{p.state}</span>
      </div>
      {open && (
        <div className="practice-detail">
          {p.address && <div className="pd-row">🏠 {p.address}</div>}
          {p.email   && <div className="pd-row">✉️ <a href={`mailto:${p.email}`}>{p.email}</a></div>}
          {p.website && p.website.startsWith('http') && (
            <div className="pd-row">🌐 <a href={p.website} target="_blank" rel="noreferrer">{p.website.replace(/^https?:\/\//,'')}</a></div>
          )}
          {p.hours && (
            <details className="pd-hours">
              <summary>🕐 Hours</summary>
              <pre>{p.hours}</pre>
            </details>
          )}
          {p.comment && <div className="pd-row pd-comment">{p.comment}</div>}
        </div>
      )}
    </div>
  )
}

// ── Aged care / Hospital card ────────────────────────────────
function FacilityCard({ p, mapType }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`practice-card${open ? ' open' : ''}`} onClick={() => setOpen(o => !o)}>
      <div className="practice-header">
        <div className="practice-name">{p.name}</div>
        <span className="practice-toggle">{open ? '▲' : '▼'}</span>
      </div>
      <div className="practice-meta">
        <span className="practice-location">📍 {p.suburb || normalizeState(p.state)}</span>
        {p.phone && <span className="practice-phone">📞 {p.phone}</span>}
      </div>
      <div className="practice-tags">
        {mapType === 'hospitals' && (
          <span className={`tag ${p.is_public ? 'bulk-billing' : 'telehealth'}`}>
            {p.is_public ? '🏛 Public' : '🏢 Private'}
          </span>
        )}
        {mapType === 'aged_care' && (
          <span className="tag" style={{background:'#14532d',color:'#4ade80',border:'1px solid #166534'}}>Aged Care</span>
        )}
        <span className="tag state-tag">{normalizeState(p.state)}</span>
      </div>
      {open && (
        <div className="practice-detail">
          {p.address  && <div className="pd-row">🏠 {p.address}</div>}
          {p.phone    && <div className="pd-row">📞 <a href={`tel:${p.phone.replace(/\s/g,'')}`}>{p.phone}</a></div>}
          {p.email    && <div className="pd-row">✉️ <a href={`mailto:${p.email}`}>{p.email}</a></div>}
          {p.website && p.website.startsWith('http') && (
            <div className="pd-row">🌐 <a href={p.website} target="_blank" rel="noreferrer">{p.website.replace(/^https?:\/\//,'')}</a></div>
          )}
          {p.phn_name && <div className="pd-row">PHN: {p.phn_name}</div>}
          {p.full_name && p.full_name !== p.name && <div className="pd-row pd-comment">{p.full_name}</div>}
          {p.notes    && <div className="pd-row pd-comment">{p.notes}</div>}
        </div>
      )}
    </div>
  )
}

// ── Config for non-medical panels ────────────────────────────
const FACILITY_URLS = {
  aged_care:   '/aged-care.geojson',
  hospitals:   '/hospitals.geojson',
  specialists: null,
}
const FACILITY_CONFIG = {
  aged_care: {
    icon: '🏡', name: 'Aged Care Facilities',
    emptyMsg: 'Click a state to filter aged care facilities.',
    filterLabel: null,
  },
  hospitals: {
    icon: '🏨', name: 'Hospitals',
    emptyMsg: 'Click a state to filter hospitals.',
    filterLabel: 'Public only',
  },
  specialists: {
    icon: '🩺', name: 'Specialists',
    placeholder: true,
  },
}

export default function StatsPanel({
  stateData, nationalData, selectedState, year, years, mapType = 'medical',
}) {
  // Medical practice data
  const [practices,  setPractices]  = useState([])
  const [search,     setSearch]     = useState('')
  const [filterBulk, setFilterBulk] = useState(false)
  const [filterTele, setFilterTele] = useState(false)

  // Non-medical facility data
  const [facilities, setFacilities] = useState([])
  const [facSearch,  setFacSearch]  = useState('')
  const [filterPub,  setFilterPub]  = useState(false)

  useEffect(() => {
    fetch('/practices.geojson')
      .then(r => r.json())
      .then(gj => setPractices(gj.features.map(f => f.properties)))
  }, [])

  useEffect(() => {
    setFacilities([])
    setFacSearch('')
    setFilterPub(false)
    if (mapType !== 'medical') {
      const url = FACILITY_URLS[mapType]
      if (url) {
        fetch(url)
          .then(r => r.json())
          .then(gj => setFacilities(gj.features.map(f => f.properties)))
          .catch(() => setFacilities([]))
      }
    }
  }, [mapType])

  // ── Non-medical panels ──────────────────────────────────────
  if (mapType !== 'medical') {
    const cfg = FACILITY_CONFIG[mapType]

    // Specialists placeholder
    if (cfg.placeholder) {
      return (
        <div className="stats-panel empty-state">
          <div className="empty-icon">{cfg.icon}</div>
          <h3>{cfg.name}</h3>
          <p>Specialist data is coming soon. This layer will show specialist practices and referral centres across Australia.</p>
          <div className="hint-list">
            <div className="hint-item">🫀 Cardiologists, Neurologists, Oncologists &amp; more</div>
            <div className="hint-item">📍 Locations across all states &amp; territories</div>
            <div className="hint-item">📞 Contact details &amp; referral information</div>
          </div>
        </div>
      )
    }

    const stateName      = STATE_FULL[selectedState] || selectedState
    const stateFacilities = facilities.filter(f =>
      !selectedState || normalizeState(f.state) === selectedState
    )
    const filteredFac = stateFacilities.filter(f => {
      const q   = facSearch.toLowerCase()
      const matchSearch = !q
        || (f.name   || '').toLowerCase().includes(q)
        || (f.suburb || '').toLowerCase().includes(q)
        || (f.postcode || '').includes(q)
        || (f.phn_name || '').toLowerCase().includes(q)
      const matchPub = !filterPub || f.is_public === true
      return matchSearch && matchPub
    })
    const pubCount = facilities.filter(f => f.is_public).length
    const stPub    = stateFacilities.filter(f => f.is_public).length

    if (!selectedState) {
      return (
        <div className="stats-panel empty-state">
          <div className="empty-icon">{cfg.icon}</div>
          <h3>Select a State</h3>
          <p>{cfg.emptyMsg}</p>
          <div className="hint-list">
            <div className="hint-item">{cfg.icon} {facilities.length.toLocaleString()} {cfg.name} nationally</div>
            {mapType === 'hospitals' && (
              <>
                <div className="hint-item">🏛 {pubCount.toLocaleString()} Public hospitals</div>
                <div className="hint-item">🏢 {(facilities.length - pubCount).toLocaleString()} Private hospitals</div>
              </>
            )}
          </div>
        </div>
      )
    }

    return (
      <div className="stats-panel">
        <div className="panel-header">
          <div>
            <h3 className="panel-state-name">{stateName}</h3>
            <span className="panel-state-code">{selectedState}</span>
          </div>
          <span className="panel-year-badge">{cfg.name}</span>
        </div>

        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">Total {cfg.name}</div>
            <div className="kpi-value blue">{stateFacilities.length}</div>
          </div>
          {mapType === 'hospitals' && (
            <>
              <div className="kpi-card">
                <div className="kpi-label">Public Hospitals</div>
                <div className="kpi-value green">{stPub}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Private Hospitals</div>
                <div className="kpi-value amber">{stateFacilities.length - stPub}</div>
              </div>
            </>
          )}
        </div>

        <div className="chart-section">
          <div className="section-label">
            {cfg.icon} {cfg.name} — {stateName}
            <span className="practice-sub-count">{stateFacilities.length} total</span>
          </div>
          <div className="practice-filters">
            <input
              className="practice-search"
              placeholder={`Search ${cfg.name.toLowerCase()}…`}
              value={facSearch}
              onChange={e => setFacSearch(e.target.value)}
            />
            {mapType === 'hospitals' && (
              <label className="filter-check">
                <input type="checkbox" checked={filterPub} onChange={e => setFilterPub(e.target.checked)} />
                Public only
              </label>
            )}
          </div>
          <div className="practice-list">
            {filteredFac.length === 0 && (
              <div className="no-results">No {cfg.name.toLowerCase()} match your filter.</div>
            )}
            {filteredFac.slice(0, 40).map((p, i) => (
              <FacilityCard key={i} p={p} mapType={mapType} />
            ))}
            {filteredFac.length > 40 && (
              <div className="more-results">…and {filteredFac.length - 40} more. Refine search.</div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // ── Medical (GP) panel ──────────────────────────────────────
  const data = selectedState ? stateData[selectedState] : null
  const name = selectedState ? STATE_FULL[selectedState] : null

  const statePractices = practices.filter(p => !selectedState || p.state === selectedState)
  const filtered = statePractices.filter(p => {
    const q = search.toLowerCase()
    const matchSearch = !q
      || p.name.toLowerCase().includes(q)
      || p.suburb.toLowerCase().includes(q)
      || p.postcode.includes(q)
    const matchBulk = !filterBulk || p.bulk_billing
    const matchTele = !filterTele || p.telehealth
    return matchSearch && matchBulk && matchTele
  })

  const totalGps   = data?.total_gps?.[year]
  const totalFte   = data?.total_gpfte?.[year]
  const vrFte      = data?.vr_gpfte?.[year]
  const traineeFte = data?.trainee_gpfte?.[year]
  const maleVal    = data?.male_gpfte?.[year]
  const femaleVal  = data?.female_gpfte?.[year]
  const maleRatio  = (totalFte && maleVal)  ? ((maleVal  / totalFte) * 100).toFixed(1) : null
  const femRatio   = (totalFte && femaleVal) ? ((femaleVal / totalFte) * 100).toFixed(1) : null
  const bulkCount  = statePractices.filter(p => p.bulk_billing).length

  const trendData = YEARS.map(y => ({
    year: y,
    'Total GPs':   data?.total_gps?.[y]     ?? null,
    'Total FTE':   data?.total_gpfte?.[y]   ?? null,
    'VR FTE':      data?.vr_gpfte?.[y]      ?? null,
    'Trainee FTE': data?.trainee_gpfte?.[y] ?? null,
  }))

  const typeBar = selectedState ? [
    { name: 'VR',      value: data?.vr_gpfte?.[year]      ?? 0 },
    { name: 'Non-VR',  value: data?.nonvr_gpfte?.[year]   ?? 0 },
    { name: 'Trainee', value: data?.trainee_gpfte?.[year] ?? 0 },
  ] : null

  if (!selectedState) {
    return (
      <div className="stats-panel empty-state">
        <div className="empty-icon">🗺️</div>
        <h3>Select a State</h3>
        <p>Click any state on the map to view GP workforce data, trends, and the real practice directory.</p>
        <div className="hint-list">
          <div className="hint-item">📊 Year-on-year trends (2020–2025)</div>
          <div className="hint-item">👨‍⚕️ GP type &amp; gender breakdown</div>
          <div className="hint-item">🏥 {practices.length.toLocaleString()} real practices with contact details</div>
          <div className="hint-item">📍 Click any practice pin on the map for details</div>
        </div>
      </div>
    )
  }

  return (
    <div className="stats-panel">
      <div className="panel-header">
        <div>
          <h3 className="panel-state-name">{name}</h3>
          <span className="panel-state-code">{selectedState}</span>
        </div>
        <span className="panel-year-badge">{year}</span>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card"><div className="kpi-label">Total GPs</div><div className="kpi-value blue">{fmt(totalGps)}</div></div>
        <div className="kpi-card"><div className="kpi-label">GP FTE</div><div className="kpi-value green">{fmt(totalFte)}</div></div>
        <div className="kpi-card"><div className="kpi-label">VR FTE</div><div className="kpi-value purple">{fmt(vrFte)}</div></div>
        <div className="kpi-card"><div className="kpi-label">Trainees FTE</div><div className="kpi-value amber">{fmt(traineeFte)}</div></div>
        <div className="kpi-card"><div className="kpi-label">Listed Practices</div><div className="kpi-value teal">{statePractices.length}</div></div>
        <div className="kpi-card"><div className="kpi-label">Bulk Billing</div><div className="kpi-value orange">{bulkCount}</div></div>
      </div>

      {maleRatio && (
        <div className="gender-bar-section">
          <div className="section-label">GP Gender Split (FTE) — {year}</div>
          <div className="gender-bar">
            <div className="gender-male"   style={{ width: `${maleRatio}%` }} title={`Male ${maleRatio}%`} />
            <div className="gender-female" style={{ width: `${femRatio}%`  }} title={`Female ${femRatio}%`} />
          </div>
          <div className="gender-labels">
            <span className="male-label">♂ {maleRatio}% ({fmt(maleVal)})</span>
            <span className="female-label">♀ {femRatio}% ({fmt(femaleVal)})</span>
          </div>
        </div>
      )}

      {typeBar && (
        <div className="chart-section">
          <div className="section-label">GP Type Breakdown — {year} (FTE)</div>
          <ResponsiveContainer width="100%" height={110}>
            <BarChart data={typeBar} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} width={52} />
              <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:6 }} formatter={v => v.toLocaleString()} />
              <Bar dataKey="value" fill="#60a5fa" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="chart-section">
        <div className="section-label">GP Workforce Trend 2020–2025</div>
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={trendData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="year" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} width={52} />
            <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:6 }} labelStyle={{ color:'#e2e8f0', fontWeight:600 }} formatter={v => [v?.toLocaleString(),'']} />
            <Legend wrapperStyle={{ fontSize:10, color:'#94a3b8' }} />
            <Line type="monotone" dataKey="Total GPs"   stroke="#60a5fa" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="Total FTE"   stroke="#34d399" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="VR FTE"      stroke="#a78bfa" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
            <Line type="monotone" dataKey="Trainee FTE" stroke="#fbbf24" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-section">
        <div className="section-label">
          🏥 Practice Directory — {name}
          <span className="practice-sub-count">{statePractices.length} practices</span>
        </div>
        <div className="practice-filters">
          <input
            className="practice-search"
            placeholder="Search name, suburb or postcode…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <label className="filter-check">
            <input type="checkbox" checked={filterBulk} onChange={e => setFilterBulk(e.target.checked)} />
            Bulk Billing only
          </label>
          <label className="filter-check">
            <input type="checkbox" checked={filterTele} onChange={e => setFilterTele(e.target.checked)} />
            Telehealth only
          </label>
        </div>
        <div className="practice-list">
          {filtered.length === 0 && <div className="no-results">No practices match your filter.</div>}
          {filtered.slice(0, 40).map((p, i) => <PracticeCard key={i} p={p} />)}
          {filtered.length > 40 && (
            <div className="more-results">…and {filtered.length - 40} more. Refine search to narrow results.</div>
          )}
        </div>
      </div>
    </div>
  )
}
"""

# ─────────────────────────────────────────────────────────────
# Write files
# ─────────────────────────────────────────────────────────────
files = {
    BASE / 'App.jsx':                       APP_JSX,
    BASE / 'components' / 'AustraliaMap.jsx': AUSTRALIA_MAP_JSX,
    BASE / 'components' / 'StatsPanel.jsx':   STATS_PANEL_JSX,
}

for path, content in files.items():
    path.write_text(content, encoding='utf-8')
    print(f'Written {path.name}: {len(content):,} chars  ({path.stat().st_size:,} bytes)')

print('All files written.')
