import { useState } from 'react'
import ItemList from './components/ItemList'
import MapView from './components/MapView'
import locations from './data/locations.json'
import './styles/app.scss'

export default function App() {
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('all')

  const types = ['all', ...new Set(locations.map(l => l.type))]

  const filtered = filter === 'all'
    ? locations
    : locations.filter(l => l.type === filter)

  return (
    <div className="app">
      <header className="app-header">
        <span className="app-header__eyebrow">Netscape / Local</span>
        <h1 className="app-header__title">Network Map</h1>
        <nav className="app-header__filters">
          {types.map(t => (
            <button
              key={t}
              className={`filter-chip${filter === t ? ' filter-chip--active' : ''}`}
              onClick={() => setFilter(t)}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>

      <div className="app-body">
        <aside className="app-list">
          <ItemList
            items={filtered}
            selected={selected}
            onSelect={setSelected}
          />
        </aside>
        <main className="app-map">
          <MapView
            items={filtered}
            selected={selected}
            onSelect={setSelected}
          />
        </main>
      </div>
    </div>
  )
}
