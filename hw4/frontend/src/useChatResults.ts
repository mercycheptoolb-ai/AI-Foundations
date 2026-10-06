import { createContext, useContext } from 'react'
import type { PageResults } from './api'

export interface ShownResults extends PageResults {
  shownAt: number // changes every time results are pushed, so the grid can animate in
  owner: number | null // user id of the shopper whose chat produced it (null = guest)
}

export interface ChatResultsState {
  results: ShownResults | null
  show: (results: PageResults) => void
  clear: () => void
}

export const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
