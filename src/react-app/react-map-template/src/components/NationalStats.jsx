import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function pct(a, b) {
  if (!a || !b) return null
  return (((b - a) / a) * 100).toFixed(1)
}

export default function NationalStats({ data, year }) {
  const prev = String(Number(year) - 1)

  const metrics = [
    { key: 'total_gps',      label: 'Total GPs',       color: '#60a5fa', prefix: '' },
    { key: 'vr',             label: 'VR GPs',           color: '#a78bfa', prefix: '' },
    { key: 'trainee',        label: 'GP Trainees',      color: '#fbbf24', prefix: '' },
    { key: 'total_patients', label: 'Patients Serviced',color: '#34d399', prefix: '' },
  ]

  // National trend bar data
  const trendData = ['2020','2021','2022','2023','2024','2025'].map(y => ({
    year: y,
    'GPs':      data.total_gps?.[y],
    'Trainees': data.trainee?.[y],
  }))

  return (
    <section className="national-stats">
      <div className="national-kpis">
        {metrics.map(m => {
          const cur  = data[m.key]?.[year]
          const prv  = data[m.key]?.[prev]
          const chg  = pct(prv, cur)
          return (
            <div className="national-kpi" key={m.key}>
              <div className="nkpi-label">{m.label}</div>
              <div className="nkpi-value" style={{ color: m.color }}>
                {cur?.toLocaleString() ?? '—'}
              </div>
              {chg && (
                <div className={`nkpi-change ${Number(chg) >= 0 ? 'up' : 'down'}`}>
                  {Number(chg) >= 0 ? '▲' : '▼'} {Math.abs(chg)}% vs {prev}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="national-trend">
        <div className="section-label">National GP Workforce 2020–2025</div>
        <ResponsiveContainer width="100%" height={80}>
          <BarChart data={trendData} margin={{ top: 2, right: 8, left: 0, bottom: 0 }} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" vertical={false} />
            <XAxis dataKey="year" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis hide />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: 12 }}
              labelStyle={{ color: '#e2e8f0', fontWeight: 600 }}
              formatter={v => v?.toLocaleString()}
            />
            <Bar dataKey="GPs"      fill="#60a5fa" radius={[2,2,0,0]} />
            <Bar dataKey="Trainees" fill="#fbbf24" radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
