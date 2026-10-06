import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { getProductsCached, type Product } from '../api'
import { openChat } from '../chatEvents'

// Scoreboard ticker under the navbar. Every number is computed from the live catalogue;
// the only urgency is real per-size stock ("ONLY 2 LEFT IN S").
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const CAT_LABELS: Record<string, string> = {
  crewneck: 'crewnecks', hoodie: 'hoodies', 't-shirt': 't-shirts', 'quarter-zip': 'quarter-zips', jacket: 'jackets', 'long-sleeve': 'long-sleeves',
}

function lowStock(products: Product[]) {
  const picks: { p: Product; size: string; qty: number }[] = []
  const seen = new Set<string>()
  const slots = products.flatMap((p) =>
    SIZES.map((size) => ({ p, size, qty: p.stock_by_size?.[size] ?? 0 })).filter((x) => x.qty >= 1 && x.qty <= 5),
  )
  slots.sort((a, b) => a.qty - b.qty || a.p.name.localeCompare(b.p.name))
  for (const s of slots) {
    if (seen.has(s.p.product_id)) continue // one size per product, for variety
    seen.add(s.p.product_id)
    picks.push(s)
    if (picks.length === 6) break
  }
  return picks
}

export default function Ticker() {
  const [products, setProducts] = useState<Product[] | null>(null)
  useEffect(() => {
    getProductsCached().then(setProducts).catch(() => setProducts(null))
  }, [])
  // Keep the 34px strip in place while loading, so the page doesn't jump when data arrives.
  if (!products?.length) return <div className="ticker" aria-hidden="true" />

  const counts: Record<string, number> = {}
  for (const p of products) if (p.category) counts[p.category] = (counts[p.category] ?? 0) + 1
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 3)

  const segments = (copy: boolean): ReactNode[] => {
    const tab = copy ? -1 : undefined
    return [
      <span key="n">{products.length} styles on the roster</span>,
      ...top.map(([k, n]) => <span key={k}>{n} {CAT_LABELS[k] ?? k}</span>),
      <span key="sizes">Sizes XS–XXL</span>,
      <span key="lic">Officially licensed</span>,
      <span key="addr">57 Broadway, New Haven</span>,
      ...lowStock(products).map(({ p, size, qty }) => (
        <Link key={p.product_id} to={`/products/${p.product_id}`} tabIndex={tab}>
          Low stock: {p.name} · only {qty} left in {size} <span aria-hidden="true">▸</span>
        </Link>
      )),
      <button key="ask" type="button" tabIndex={tab} onClick={() => openChat()}>
        Ask the Bulldog Assistant for your size <span aria-hidden="true">▸</span>
      </button>,
    ]
  }
  const first = segments(false)
  return (
    <div className="ticker" role="region" aria-label="Store scoreboard">
      <div className="ticker-track" style={{ animationDuration: `${first.length * 3.5}s` }}>
        <div className="ticker-group">{first}</div>
        <div className="ticker-group" aria-hidden="true">{segments(true)}</div>
      </div>
    </div>
  )
}
