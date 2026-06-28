import './ItemList.scss'

const STATUS_LABEL = {
  online: '● Online',
  idle: '◎ Idle',
  visible: '◌ Visible',
}

export default function ItemList({ items, selected, onSelect }) {
  return (
    <ul className="item-list">
      {items.map(item => (
        <li
          key={item.id}
          className={`item-card${selected?.id === item.id ? ' item-card--active' : ''} item-card--${item.status}`}
          onClick={() => onSelect(selected?.id === item.id ? null : item)}
        >
          <div className="item-card__header">
            <span className="item-card__name">{item.name}</span>
            <span className={`item-card__badge item-card__badge--${item.status}`}>
              {STATUS_LABEL[item.status] ?? item.status}
            </span>
          </div>
          <div className="item-card__meta">
            <span className="item-card__type">{item.type}</span>
            {item.address && <code className="item-card__ip">{item.address}</code>}
            {item.signal != null && (
              <span className="item-card__signal">{item.signal} dBm · {item.band}</span>
            )}
          </div>
          <p className="item-card__desc">{item.description}</p>
        </li>
      ))}
    </ul>
  )
}
