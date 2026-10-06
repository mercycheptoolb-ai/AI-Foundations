import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Jersey from '../components/Jersey'
import { useAuth } from '../useAuth'

const MIN_PASSWORD = 8

export default function Signup() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const tooShort = password.length > 0 && password.length < MIN_PASSWORD
  const mismatch = confirm.length > 0 && confirm !== password

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (password.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters.`)
      return
    }
    if (password !== confirm) {
      setError('Passwords don’t match.')
      return
    }
    setSubmitting(true)
    try {
      await signup({ first_name: firstName, last_name: lastName, email, password })
      navigate('/', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  if (user)
    return (
      <div className="auth">
        <h1>You already have an account</h1>
        <p className="muted">
          You’re signed in as <strong>{user.email}</strong>.
        </p>
        <Link to="/products" className="btn">
          Start shopping
        </Link>
      </div>
    )

  return (
    <div className="signup-wrap">
    <figure className="signup-jersey">
      <Jersey name={firstName || 'CUSTOMS'} number="57" />
      <figcaption>Your name on the jersey. Your account saves your chats with the Bulldog Assistant.</figcaption>
    </figure>
    <div className="auth">
      <h1>Create your account</h1>
      <p className="muted">Save your chats and get personalized picks.</p>
      <form onSubmit={handleSubmit}>
        <div className="row">
          <div className="field">
            <label htmlFor="signup-first">First name</label>
            <input
              id="signup-first"
              required
              maxLength={50}
              autoComplete="given-name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="signup-last">Last name</label>
            <input
              id="signup-last"
              required
              maxLength={50}
              autoComplete="family-name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
          </div>
        </div>
        <div className="field">
          <label htmlFor="signup-email">Email</label>
          <input
            id="signup-email"
            type="email"
            required
            maxLength={254}
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="signup-password">Password</label>
          <div className="password-field">
            <input
              id="signup-password"
              type={showPassword ? 'text' : 'password'}
              required
              minLength={MIN_PASSWORD}
              maxLength={128}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={tooShort}
              aria-describedby="signup-password-hint"
            />
            <button
              type="button"
              className="toggle"
              onClick={() => setShowPassword((s) => !s)}
              aria-pressed={showPassword}
              aria-controls="signup-password signup-confirm"
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          <span id="signup-password-hint" className={`hint ${tooShort ? 'bad' : ''}`}>
            At least {MIN_PASSWORD} characters
          </span>
        </div>
        <div className="field">
          <label htmlFor="signup-confirm">Confirm password</label>
          <input
            id="signup-confirm"
            type={showPassword ? 'text' : 'password'}
            required
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            aria-invalid={mismatch}
            aria-describedby={mismatch ? 'signup-confirm-hint' : undefined}
          />
          {mismatch && (
            <span id="signup-confirm-hint" className="hint bad">
              Passwords don’t match
            </span>
          )}
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="btn" type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create Account'}
        </button>
      </form>
      <p className="muted">
        Already have an account?{' '}
        <Link to="/login" className="link">
          Log in
        </Link>
      </p>
    </div>
    </div>
  )
}
