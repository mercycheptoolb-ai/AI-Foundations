import { useCallback, useEffect, useState, type ReactNode } from 'react'
import * as api from './api'
import type { SignupInput, User } from './api'
import { AuthContext } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Re-read the session from the HttpOnly cookie. Only replace `user` when the account
  // actually changed, so components keyed by user id don't remount needlessly.
  const refresh = useCallback(async () => {
    try {
      const fresh = await api.getCurrentUser()
      setUser((cur) => (cur?.id === fresh?.id ? cur : fresh))
    } catch {
      // network hiccup: keep what we have
    }
  }, [])

  // Restore the session on page load...
  useEffect(() => {
    api
      .getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  // ...and re-check when the shopper comes back to this tab (they may have logged out or
  // into another account in a different tab, or the session may have expired).
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', refresh)
    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', refresh)
    }
  }, [refresh])

  const login = useCallback(async (email: string, password: string) => {
    const { user } = await api.login(email, password)
    setUser(user)
    return user
  }, [])

  const signup = useCallback(async (input: SignupInput) => {
    const { user } = await api.signup(input)
    setUser(user)
    return user
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } finally {
      setUser(null)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  )
}
