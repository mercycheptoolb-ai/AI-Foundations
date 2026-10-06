export type AgentStatus = 'idle' | 'thinking' | 'done' | 'error'

export interface SpecialistMeta {
  book_number: number
  title: string
  short: string
  specialty: string
  accent: string
  house_hint: string
  page_count?: number
  token_count?: number
}

export interface Delegation {
  agent: string
  book_number: number
  book_title: string
  question: string
  reply: string
  status: 'pending' | 'running' | 'done' | 'error'
}

export type ModelName = 'gpt-6-luna' | 'gpt-6-astra'

/** USD per 1M tokens. */
export interface ModelPrice {
  input: number
  cached_input: number
  output: number
}

/** Running token + dollar tally for one agent. */
export interface SpendRow {
  agent: string
  book_number: number | null
  requests: number
  input_tokens: number
  cached_tokens: number
  output_tokens: number
  cost_usd: number
}

export interface ChatResult {
  answer: string
  delegations: Delegation[]
  trace?: unknown[]
  boss_name: string
  spend?: SpendRow[]
  total_usd?: number
  budget_exceeded?: boolean
}

export interface ProgressEvent {
  type: string
  data: Record<string, unknown>
}
