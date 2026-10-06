import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getProductsCached, type Product } from '../api'
import { openChat } from '../chatEvents'
import BulldogPatch from '../components/BulldogPatch'
import CountUp from '../components/CountUp'
import Jersey from '../components/Jersey'
import Pennants from '../components/Pennants'
import ProductCard from '../components/ProductCard'
import { useRoster } from '../roster'

// Hand-picked (not "best sellers": we don't have sales data, so we don't claim it).
const FEATURED_IDS = [
  'basic-hoodie-big-yale',
  '2025-yale-vs-harvard-t-shirt',
  'champion-reverse-weave-crewneck',
  'brooks-brothers-bomber-jacket-yale',
]

const BENCH_QUESTIONS = ['Which hoodies are in stock in M?', 'Gift ideas under $50', 'Show me residential college gear']

export default function Home() {
  const [all, setAll] = useState<Product[]>([])
  const { setRoster } = useRoster()
  const { pathname } = useLocation()

  useEffect(() => {
    getProductsCached()
      .then(setAll)
      .catch(() => setAll([]))
  }, [])

  const picks = FEATURED_IDS.map((id) => all.find((p) => p.product_id === id)).filter((p): p is Product => Boolean(p))
  const featured = picks.length ? picks : all.slice(0, 4)
  const categories = new Set(all.map((p) => p.category).filter(Boolean)).size

  // The starting lineup is numbered #01-#04, and the chat understands those numbers.
  useEffect(() => {
    if (featured.length) setRoster({ path: pathname, items: featured.map((p) => ({ id: p.product_id, name: p.name })) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [all, pathname])

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Officially licensed · 57 Broadway, New Haven</p>
          <h1>
            Bulldog pride,
            <br />
            <span className="accent">made to wear.</span>
          </h1>
          <p className="lead">
            Cozy hoodies, everyday tees, and college crewnecks for students, alumni, and every fan
            cheering from the stands.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn">
              Shop the collection
            </Link>
            <button type="button" className="btn btn-ghost" onClick={() => openChat()}>
              Ask the Bulldog Assistant
            </button>
            <Link to="/about" className="link hero-story">
              Our story →
            </Link>
          </div>
        </div>
        <div className="hero-locker" aria-hidden="true">
          <div className="locker-cubby">
            <div className="hero-jersey">
              <Jersey />
            </div>
          </div>
          {all.length > 0 && (
            <div className="stat-row">
              <span>
                <b><CountUp value={all.length} digits={3} /></b> styles
              </span>
              <span>
                <b><CountUp value={categories} /></b> categories
              </span>
              <span>
                <b>XS–XXL</b> sizes
              </span>
            </div>
          )}
        </div>
      </section>

      <Pennants />

      {featured.length > 0 && (
        <section>
          <div className="section-head">
            <div>
              <p className="eyebrow">Hand-picked</p>
              <h2>Starting lineup</h2>
              <p className="muted lineup-sub">Four picks from the roster. Ask the assistant about any of them by number (“is #2 in M?”).</p>
            </div>
            <Link to="/products" className="link">
              View all →
            </Link>
          </div>
          <div className="grid">
            {featured.map((p, i) => (
              <ProductCard key={p.product_id} product={p} number={i + 1} />
            ))}
          </div>
        </section>
      )}

      <section className="bench" aria-label="Get help from the Bulldog Assistant">
        <span className="bench-patch">
          <BulldogPatch size={48} />
        </span>
        <div className="bench-copy">
          <h3>Not sure about a size?</h3>
          <p className="muted">
            The Bulldog Assistant checks stock by size and color, and finds similar styles when your size is gone.
          </p>
          <div className="playbook" role="group" aria-label="Ask the Bulldog Assistant">
            {BENCH_QUESTIONS.map((q) => (
              <button key={q} type="button" className="chip-btn" onClick={() => openChat(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
