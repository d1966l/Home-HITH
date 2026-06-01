import { useEffect, useState } from 'react'
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
          <span className="tag" style={{background:'#14532d',color:'#4ade80',border:'1px solid #166534'}}>{p.care_type || 'Aged Care'}</span>
        )}
        <span className="tag state-tag">{normalizeState(p.state)}</span>
      </div>
      {open && (
        <div className="practice-detail">
          {p.address  && <div className="pd-row">🏠 {p.address}</div>}
          {p.phone    && <div className="pd-row">📞 <a href={`tel:${p.phone.replace(/\s/g,'')}`}>{p.phone}</a></div>}
          {p.email    && <div className="pd-row">✉️ <a href={`mailto:${p.email}`}>{p.email}</a></div>}
          {p.url && p.url.startsWith('http') && (
            <div className="pd-row">🌐 <a href={p.url} target="_blank" rel="noreferrer">My Aged Care ↗</a></div>
          )}
          {p.website && p.website.startsWith('http') && (
            <div className="pd-row">🌐 <a href={p.website} target="_blank" rel="noreferrer">{p.website.replace(/^https?:\/\//,'')}</a></div>
          )}
          {p.phn_name && <div className="pd-row">PHN: {p.phn_name}</div>}
          {p.provider && p.provider !== p.name && <div className="pd-row pd-comment">Provider: {p.provider}</div>}
          {p.care_type && <div className="pd-row pd-comment">Type: {p.care_type}</div>}
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
