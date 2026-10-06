import { createContext, useContext, useState, type ReactNode } from 'react'

// "Call a number": the cards on screen, in order. Card #7 in the grid is items[6], and
// the chat expands "#7" into that product before asking the assistant.
export interface Roster {
  path: string // the page it belongs to; ignored on any other page
  items: { id: string; name: string }[]
}

interface RosterState {
  roster: Roster | null
  setRoster: (r: Roster | null) => void
}

const RosterContext = createContext<RosterState>({ roster: null, setRoster: () => {} })

export function RosterProvider({ children }: { children: ReactNode }) {
  const [roster, setRoster] = useState<Roster | null>(null)
  return <RosterContext.Provider value={{ roster, setRoster }}>{children}</RosterContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useRoster = () => useContext(RosterContext)
