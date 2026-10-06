import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProductsCached, type Product } from '../api'
import { matchesText } from '../catalog'
import { openChat } from '../chatEvents'

// Pennant wall: one tap to "your" shelf. Live counts; pennants with no gear are hidden.
const ROWS: { title: string; items: { label: string; q: string }[] }[] = [
  {
    title: 'Your college',
    items: ['Benjamin Franklin', 'Berkeley', 'Branford', 'Davenport', 'Ezra Stiles', 'Grace Hopper', 'Jonathan Edwards', 'Morse', 'Pauli Murray', 'Pierson', 'Saybrook', 'Silliman', 'Timothy Dwight', 'Trumbull'].map((c) => ({ label: c, q: c })),
  },
  {
    title: 'The family line',
    items: [
      { label: 'Yale Dad', q: 'yale dad' }, { label: 'Yale Mom', q: 'yale mom' }, { label: 'Grandpa', q: 'grandpa' },
      { label: 'Grandma', q: 'grandma' }, { label: 'Aunt', q: 'aunt' }, { label: 'Uncle', q: 'uncle' },
      { label: 'Brother', q: 'yale brother' }, { label: 'Cousin', q: 'cousin' },
    ],
  },
  {
    title: 'Teams & schools',
    items: ['Hockey', 'Football', 'Baseball', 'Squash', 'Sailing', 'Fencing', 'Tennis', 'Soccer', 'School of Art', 'Architecture', 'Law School', 'School of Medicine'].map((t) => ({ label: t, q: t })),
  },
]

export default function Pennants() {
  const [products, setProducts] = useState<Product[]>([])
  useEffect(() => {
    getProductsCached().then(setProducts).catch(() => setProducts([]))
  }, [])
  const rows = useMemo(
    () =>
      ROWS.map((row) => ({
        ...row,
        items: row.items
          .map((it) => ({ ...it, n: products.filter((p) => matchesText(p, it.q.toLowerCase())).length }))
          .filter((it) => it.n > 0),
      })),
    [products],
  )
  if (!products.length) return null
  return (
    <section className="pennant-wall" aria-labelledby="pennant-title">
      <p className="eyebrow">Rep yours</p>
      <h2 id="pennant-title">Your college. Your team. Your family.</h2>
      {rows.map((row) => (
        <div key={row.title} className="pennant-row-wrap">
          <p className="pennant-row-title">{row.title}</p>
          <div className="pennant-row">
            {row.items.map((it) => (
              <Link key={it.label} to={`/products?q=${encodeURIComponent(it.q)}`} className="pennant">
                <span className="pennant-label">{it.label}</span>
                <span className="pennant-count">{it.n} {it.n === 1 ? 'style' : 'styles'}</span>
              </Link>
            ))}
          </div>
        </div>
      ))}
      <button type="button" className="pennant pennant-ask" onClick={() => openChat('Do you have gear for my residential college?')}>
        <span className="pennant-label">Don’t see yours?</span>
        <span className="pennant-count">Ask the Bulldog Assistant</span>
      </button>
    </section>
  )
}
