import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { formatPrice, getProduct, type ProductDetail } from '../api'
import { openChat } from '../chatEvents'
import { stageAttrs, usePhotoStage } from '../usePhotoStage'

const LOW_STOCK = 5

// Swatch dots for the colour names the catalogue uses (unknown names get no dot).
const SWATCH: Record<string, string> = {
  navy: '#1f2a44', 'navy blue': '#1f2a44', 'heather gray': '#b9b6b1', 'light heather gray': '#cfccc7',
  gray: '#8e8e93', 'charcoal gray': '#3a3a3f', 'dark heather gray': '#5b5b60', white: '#f6f3ef',
  black: '#0b0b0c', red: '#c8102e', blue: '#2f5fb3', gold: '#d4a017', yellow: '#e8c547', cream: '#efe6d2',
}

function Whistle() {
  return (
    <svg className="whistle" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <circle cx="9" cy="14" r="6" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <path d="M13 9 L21 6 L21 11 L14.5 12" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
      <circle cx="9" cy="14" r="1.6" fill="currentColor" />
    </svg>
  )
}

export default function ProductPage() {
  const { productId = '' } = useParams()
  // Where the shopper came from (a filtered list or chat results), so the back link returns there.
  const from = (useLocation().state as { from?: string } | null)?.from
  const backTo = from && from.startsWith('/products') ? from : '/products'
  const backLabel = backTo === '/products' ? '← All products' : '← Back to results'
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [error, setError] = useState('')
  const { stage, onLoad } = usePhotoStage(product?.image_url ?? '')

  useEffect(() => {
    setProduct(null)
    setError('')
    getProduct(productId)
      .then(setProduct)
      .catch((e: Error) =>
        setError(e.message === 'Not found' ? 'We couldn’t find that product.' : 'Could not load this product.'),
      )
  }, [productId])

  if (error)
    return (
      <div className="empty">
        <p className="error">{error}</p>
        <Link to="/products" className="btn">
          Back to products
        </Link>
      </div>
    )
  if (!product) return <p className="muted">Loading…</p>

  const inStock = product.sizes.some((s) => s.quantity > 0)
  const soldOutSizes = product.sizes.filter((s) => s.quantity === 0).map((s) => s.size)
  const swatch = product.colors[0] ? SWATCH[product.colors[0].toLowerCase()] : undefined

  return (
    <>
      <Link to={backTo} className="link back">
        {backLabel}
      </Link>
      <div className="detail">
        <div className="detail-img" {...stageAttrs(stage)}>
          <img src={product.image_url} alt={product.name} onLoad={onLoad} />
        </div>
        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price big">{formatPrice(product.price)}</p>
          <button className="btn btn-small ask-item" onClick={() => openChat()}>
            <Whistle /> Ask about this item
          </button>
          {/* Playbook: one tap asks the assistant about this item (page context says which) */}
          <div className="playbook" role="group" aria-label="Quick questions about this item">
            {['Which sizes are in stock?', 'What color is it?', 'Show me similar items'].map((q) => (
              <button key={q} type="button" className="chip-btn" onClick={() => openChat(q)}>
                {q}
              </button>
            ))}
          </div>
          <div className="scouting">
            <span className="scouting-label">Scouting report</span>
            <p>{product.description || 'No description on file yet: ask the Bulldog Assistant about this item.'}</p>
          </div>

          {/* The catalogue lists every color on the item: garment color first, then the print. */}
          {product.colors.length > 0 && (
            <>
              <h4>Color</h4>
              <div className="chips">
                <span className="chip">
                  {swatch && <span className="swatch" style={{ background: swatch }} aria-hidden="true" />}
                  {product.colors[0]}
                </span>
              </div>
              {product.colors.length > 1 && (
                <p className="muted print-colors">Print colors: {product.colors.slice(1).join(', ')}</p>
              )}
            </>
          )}

          <h4>Sizes &amp; stock</h4>
          <div className="sizes">
            {product.sizes.map((s) => (
              <div key={s.size} className={`size ${s.quantity === 0 ? 'out' : s.quantity <= LOW_STOCK ? 'low' : ''}`}>
                <strong>{s.size}</strong>
                <span>
                  {s.quantity === 0
                    ? 'Sold out'
                    : s.quantity <= LOW_STOCK
                      ? `Only ${s.quantity} left`
                      : `${s.quantity} in stock`}
                </span>
              </div>
            ))}
          </div>
          {!inStock && <p className="error">This item is currently sold out in every size.</p>}
          {/* Sold-out sizes are a dead end: hand them to the assistant to find similar in stock */}
          {soldOutSizes.length > 0 && (
            <div className="rescue">
              <button
                type="button"
                className="chip-btn ask-rescue"
                onClick={() =>
                  openChat(
                    soldOutSizes.length === 1
                      ? `Show me items similar to this one that are in stock in ${soldOutSizes[0]}`
                      : `This is sold out in ${soldOutSizes.join(', ')}. Show me similar items in stock in those sizes`,
                  )
                }
              >
                Sold out in {soldOutSizes.join(', ')}? Find similar in stock
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
