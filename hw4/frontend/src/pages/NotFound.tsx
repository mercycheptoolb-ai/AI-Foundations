import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="empty not-found">
      <p className="eyebrow">Fumble</p>
      <div className="led-404" aria-hidden="true">404</div>
      <h1>Page not found</h1>
      <p className="muted">This page wandered off campus.</p>
      <Link to="/" className="btn">
        Back home
      </Link>
    </div>
  )
}
