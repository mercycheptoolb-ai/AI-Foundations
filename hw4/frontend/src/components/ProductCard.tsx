import { Link, useLocation } from 'react-router-dom'
import { formatPrice, shortText } from '../api'
import { stageAttrs, usePhotoStage } from '../usePhotoStage'

// Anything with these fields can be a card: catalogue products from /api/products and
// the products the chat puts on the page (Problem 7) share this one component, so every
// card opens the same product page when clicked.
export interface CardProduct {
  product_id: string
  name: string
  price: number
  image_url: string
  description?: string
  short_description?: string
  total_stock?: number
  in_stock_sizes?: string[]
  stock_by_size?: Record<string, number>
}

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

// Which sizes can actually be bought (from per-size stock, or the chat's in-stock list).
function sizeRun(p: CardProduct): { size: string; ok: boolean }[] | null {
  if (p.stock_by_size) return SIZES.map((s) => ({ size: s, ok: (p.stock_by_size?.[s] ?? 0) > 0 }))
  if (p.in_stock_sizes) return SIZES.map((s) => ({ size: s, ok: p.in_stock_sizes!.includes(s) }))
  return null
}

export default function ProductCard({
  product,
  index = 0,
  note,
  number,
}: {
  product: CardProduct
  index?: number
  note?: string // e.g. "Only 2 left in M" when the shopper filtered by size
  number?: number // jersey number: position in the lineup on screen ("Call a number")
}) {
  const location = useLocation()
  const { stage, onLoad } = usePhotoStage(product.image_url)
  const soldOut = product.total_stock === 0 || product.in_stock_sizes?.length === 0
  const blurb = product.short_description ?? shortText(product.description ?? '')
  const run = sizeRun(product)
  const inStock = run?.filter((r) => r.ok).map((r) => r.size) ?? []
  return (
    <Link
      to={`/products/${product.product_id}`}
      state={{ from: location.pathname + location.search }} // so "Back to results" keeps filters
      className={`card${soldOut ? ' is-sold-out' : ''}`}
      data-product-id={product.product_id}
      style={{ animationDelay: `${Math.min(index, 12) * 40}ms` }}
    >
      <div className="card-img" {...stageAttrs(stage)}>
        <img src={product.image_url} alt={product.name} loading="lazy" onLoad={onLoad} />
        {soldOut && <span className="badge">Sold out</span>}
        {!soldOut && note && <span className="badge badge-low">{note}</span>}
        {number !== undefined && (
          <span className={`jersey${number > 99 ? ' three' : ''}`} aria-hidden="true">
            {String(number).padStart(2, '0')}
          </span>
        )}
      </div>
      <div className="card-body">
        <h3>{product.name}</h3>
        <p className="price">{formatPrice(product.price)}</p>
        {blurb && <p className="muted">{blurb}</p>}
        {run && (
          <p className="size-run" aria-label={inStock.length ? `In stock: ${inStock.join(', ')}` : 'Sold out in every size'}>
            {run.map((r) => (
              <span key={r.size} className={r.ok ? 'in' : 'out'} aria-hidden="true">
                {r.size}
              </span>
            ))}
          </p>
        )}
      </div>
    </Link>
  )
}
