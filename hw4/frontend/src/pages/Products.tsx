import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { getProductsCached, type Product } from '../api'
import { matchesText, reducedMotion } from '../catalog'
import { openChat } from '../chatEvents'
import CountUp from '../components/CountUp'
import ProductCard from '../components/ProductCard'
import { useRoster } from '../roster'
import { useChatResults } from '../useChatResults'

// Problem 9: shop filters. Every filter lives in the URL, so Back / refresh / sharing keep it.
const CATEGORIES: { key: string; label: string; one: string }[] = [
  { key: 'hoodie', label: 'Hoodies', one: 'hoodie' },
  { key: 'crewneck', label: 'Crewnecks', one: 'crewneck' },
  { key: 't-shirt', label: 'T-shirts', one: 't-shirt' },
  { key: 'quarter-zip', label: 'Quarter-zips', one: 'quarter-zip' },
  { key: 'jacket', label: 'Jackets', one: 'jacket' },
  { key: 'long-sleeve', label: 'Long-sleeves', one: 'long-sleeve' },
]
const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
const SORTS: Record<string, string> = {
  featured: 'Featured (best availability)',
  price_asc: 'Price: low to high',
  price_desc: 'Price: high to low',
  name: 'Name: A to Z',
}
const LOW_STOCK = 5

export default function Products() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [params, setParams] = useSearchParams()
  const searchRef = useRef<HTMLInputElement>(null)
  const query = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const size = params.get('size') ?? ''
  const sort = params.get('sort') ?? 'featured'

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('view') // filtering means browsing the catalogue, not chat results
    setParams(next, { replace: key === 'q' }) // don't flood history while typing
  }
  const navigate = useNavigate()
  const { results, clear } = useChatResults()

  // /products?view=chat shows the grid the chat assistant last put on the page.
  const chatView = params.get('view') === 'chat' && results !== null

  useEffect(() => {
    getProductsCached()
      .then(setProducts)
      .catch(() => setError('Could not load products. Is the backend running?'))
      .finally(() => setLoading(false))
  }, [])

  // New chat results arrived: bring the shopper to the top of the grid.
  useEffect(() => {
    if (chatView) window.scrollTo({ top: 0, behavior: reducedMotion() ? 'auto' : 'smooth' })
  }, [chatView, results?.shownAt])

  // Products matching everything except the category, so each pill can show its count.
  const base = useMemo(() => {
    const q = query.trim().toLowerCase()
    return products.filter((p) => matchesText(p, q) && (!size || (p.stock_by_size?.[size] ?? 0) > 0))
  }, [products, query, size])

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const p of base) if (p.category) c[p.category] = (c[p.category] ?? 0) + 1
    return c
  }, [base])

  const visible = useMemo(() => {
    const list = category ? base.filter((p) => p.category === category) : [...base]
    const sizesInStock = (p: Product) => Object.values(p.stock_by_size ?? {}).filter((n) => n > 0).length
    if (sort === 'featured')
      // Featured: items you're most likely to get in your size first (most sizes in stock,
      // then most units), so the first screen isn't full of sold-out-in-most-sizes items.
      list.sort((a, b) => sizesInStock(b) - sizesInStock(a) || (b.total_stock ?? 0) - (a.total_stock ?? 0) || a.name.localeCompare(b.name))
    else if (sort === 'price_asc') list.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
    else if (sort === 'price_desc') list.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
    else if (sort === 'name') list.sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [base, category, sort])

  // "Call a number": publish the lineup on screen so "#7" in the chat means card #7 here.
  const { setRoster } = useRoster()
  const { pathname } = useLocation()
  const lineup = chatView && results ? results.products : visible
  useEffect(() => {
    setRoster({ path: pathname, items: lineup.map((p) => ({ id: p.product_id, name: p.name })) })
  }, [lineup, pathname, setRoster])

  const filtersOn = Boolean(query || category || size || sort !== 'featured')
  const cat = CATEGORIES.find((c) => c.key === category)
  const catLabel = cat ? (visible.length === 1 ? cat.one : cat.label.toLowerCase()) : 'items'

  function showAll() {
    clear()
    navigate('/products')
  }

  if (chatView && results) {
    return (
      <>
        {/* Play Call: the assistant's search, shown as an LED scoreboard */}
        <div className="chat-results-banner" role="status">
          <div className="banner-copy">
            <span className="eyebrow">Play call · From your chat</span>
            <h1>{results.title}</h1>
            <p className="muted">
              {results.total_found} {results.total_found === 1 ? 'item' : 'items'} · click any card for details
            </p>
            <button className="btn btn-ghost btn-small" onClick={showAll}>
              Show all products
            </button>
          </div>
          <div className="scoreboard" aria-hidden="true" key={results.shownAt}>
            <span className="scoreboard-label">On the field</span>
            <span className="scoreboard-digits">
              <CountUp value={results.total_found} />
            </span>
          </div>
        </div>
        {/* key changes with each new chat result so the cards run out of the tunnel again */}
        <div className="grid grid-animate" key={results.shownAt}>
          {results.products.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} number={i + 1} />
          ))}
        </div>
      </>
    )
  }

  return (
    <>
      <div className="section-head">
        <div>
          <p className="eyebrow">The roster</p>
          <h1>Products</h1>
          <p className="muted" aria-live="polite">
            {loading
              ? 'Loading…'
              : `${visible.length} ${category ? catLabel : visible.length === 1 ? 'item' : 'items'}${size ? ` in stock in ${size}` : ''}`}
          </p>
        </div>
        <input
          className="search"
          type="search"
          placeholder="Search hoodies, colleges, colors…"
          ref={searchRef}
          value={query}
          onChange={(e) => setFilter('q', e.target.value)}
          aria-label="Search products"
        />
      </div>

      <div className="filters" role="group" aria-label="Filter products">
        <div className="pills">
          <button className={`pill ${category === '' ? 'active' : ''}`} onClick={() => setFilter('category', '')} aria-pressed={category === ''}>
            All <span>{base.length}</span>
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              className={`pill ${category === c.key ? 'active' : ''}`}
              onClick={() => setFilter('category', category === c.key ? '' : c.key)}
              aria-pressed={category === c.key}
              disabled={!counts[c.key] && category !== c.key}
            >
              {c.label} <span>{counts[c.key] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="filter-selects">
          <label>
            In stock in
            <select value={size} onChange={(e) => setFilter('size', e.target.value)} aria-label="In stock in size">
              <option value="">Any size</option>
              {SIZES.map((sz) => (
                <option key={sz} value={sz}>
                  {sz}
                </option>
              ))}
            </select>
          </label>
          <label>
            Sort
            <select value={sort} onChange={(e) => setFilter('sort', e.target.value === 'featured' ? '' : e.target.value)} aria-label="Sort products">
              {Object.entries(SORTS).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          {filtersOn && (
            <button
              className="link clear-filters"
              onClick={() => {
                setParams(new URLSearchParams())
                searchRef.current?.focus() // the button disappears; keep keyboard focus nearby
              }}
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      <div className="grid">
        {visible.map((p, i) => {
          const left = size ? (p.stock_by_size?.[size] ?? 0) : 0
          return (
            <ProductCard
              key={p.product_id}
              product={p}
              note={size && left > 0 && left <= LOW_STOCK ? `Only ${left} left in ${size}` : undefined}
              number={i + 1}
            />
          )
        })}
      </div>
      {!loading && !error && visible.length === 0 && (
        <div className="empty">
          <p className="muted">No products match these filters.</p>
          <div className="empty-actions">
            <button className="btn btn-ghost" onClick={() => setParams(new URLSearchParams())}>
              Clear filters
            </button>
            {/* Dead end -> hand it to the assistant, which can find close in-stock options */}
            <button
              type="button"
              className="chip-btn ask-rescue"
              onClick={() =>
                openChat(
                  query
                    ? `Do you have anything like "${query}"${size ? ` in stock in ${size}` : ''}?`
                    : `Find ${cat ? cat.label.toLowerCase() : 'items'} in stock in ${size || 'my size'}`,
                )
              }
            >
              {query ? `Ask the Bulldog Assistant about “${query}”` : `Find ${cat ? cat.label.toLowerCase() : 'items'} in stock${size ? ` in ${size}` : ''}`}
            </button>
          </div>
        </div>
      )}
    </>
  )
}
