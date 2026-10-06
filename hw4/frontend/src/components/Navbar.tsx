import { useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../useAuth'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function Navbar() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [logoutError, setLogoutError] = useState('')

  async function handleLogout() {
    setLogoutError('')
    try {
      await logout()
      navigate('/')
    } catch {
      setLogoutError('Couldn’t reach the server, so you may still be signed in. Please try again.')
    }
  }

  // Send shoppers back to the page they were on after logging in.
  const loginState = ['/login', '/signup'].includes(location.pathname)
    ? undefined
    : { from: location.pathname }

  return (
    <header className="navbar">
      <NavLink to="/" className="brand">
        Campus<span>Customs</span>
      </NavLink>
      <nav className="nav-links">
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end}>
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="nav-auth">
        {loading ? null : user ? (
          <>
            <span className="greeting">
              Hi, <strong>{user.first_name}</strong>
            </span>
            <button className="btn btn-small btn-ghost" onClick={handleLogout}>
              Log Out
            </button>
          </>
        ) : (
          <>
            <NavLink to="/login" state={loginState}>
              Log In
            </NavLink>
            <NavLink to="/signup" className="btn btn-small btn-ghost">
              Create Account
            </NavLink>
          </>
        )}
      </div>
      {logoutError && (
        <p className="nav-error" role="alert">
          {logoutError}
        </p>
      )}
    </header>
  )
}
