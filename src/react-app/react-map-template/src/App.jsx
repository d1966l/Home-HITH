import { useState } from 'react'
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
