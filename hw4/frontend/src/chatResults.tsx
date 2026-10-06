import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import type { PageResults } from './api'
import { useAuth } from './useAuth'
import { ChatResultsContext, type ShownResults } from './useChatResults'

// Holds the product grid the chat last put on the page. Kept in sessionStorage so the
// grid survives a refresh and the Back button after opening a product.
const STORAGE_KEY = 'cc-chat-results'

function load(): ShownResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ShownResults) : null
  } catch {
    return null
  }
}

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ShownResults | null>(load)
  const { user, loading } = useAuth()
  const lastUser = useRef<number | null | undefined>(undefined)

  const owner = loading ? undefined : (user?.id ?? null)

  const show = useCallback(
    (r: PageResults) => {
      const next = { ...r, shownAt: Date.now(), owner: owner ?? null }
      setResults(next)
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    },
    [owner],
  )

  const clear = useCallback(() => {
    setResults(null)
    sessionStorage.removeItem(STORAGE_KEY)
  }, [])

  // A different shopper logging in or out starts with a clean page. This also catches a
  // grid saved before a reload by someone who has since logged out in another tab.
  useEffect(() => {
    if (loading) return
    const id = user?.id ?? null
    if (lastUser.current !== undefined && lastUser.current !== id) clear()
    else if (results && results.owner !== undefined && results.owner !== id) clear()
    lastUser.current = id
  }, [user, loading, clear, results])

  return <ChatResultsContext.Provider value={{ results, show, clear }}>{children}</ChatResultsContext.Provider>
}
