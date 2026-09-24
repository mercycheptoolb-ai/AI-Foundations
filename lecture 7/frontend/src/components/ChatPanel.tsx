import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { sendChat } from '../api'
import Markdown from './Markdown'

export interface AskRequest {
  id: number
  text: string
}

interface Message {
  id: number
  role: 'user' | 'assistant'
  text: string
  tools?: string[]
  error?: boolean
}

const SUGGESTIONS = [
  'Which finance electives run in Fall 2?',
  'What does Uri Simonsohn teach, and when?',
  'Find marketing courses that meet on Tuesdays',
  "What's the latest research from the faculty teaching private equity?",
]

const TOOL_ICONS: Record<string, string> = {
  search_courses: '🔍',
  web_search: '🌐',
}

export default function ChatPanel({ askRequest }: { askRequest: AskRequest | null }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const nextId = useRef(1)
  const listRef = useRef<HTMLDivElement>(null)

  const send = useCallback(async (raw: string) => {
    const text = raw.trim()
    if (!text || busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setInput('')
    setMessages((m) => [...m, { id: nextId.current++, role: 'user', text }])
    try {
      const res = await sendChat(text)
      setMessages((m) => [
        ...m,
        { id: nextId.current++, role: 'assistant', text: res.reply || '(empty reply)', tools: res.tools_used },
      ])
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      setMessages((m) => [
        ...m,
        { id: nextId.current++, role: 'assistant', text: `Couldn't reach the agent: ${detail}`, error: true },
      ])
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    if (askRequest) void send(askRequest.text)
  }, [askRequest, send])

  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send(input)
    }
  }

  return (
    <aside className="chat glass" aria-label="Course assistant chat">
      <div className="chat__header">
        <div className="chat__avatar" aria-hidden>
          ⚡
        </div>
        <div>
          <h2 className="chat__title">Course Agent</h2>
          <p className="chat__subtitle">Catalog search + live web search</p>
        </div>
      </div>

      <div className="chat__list" ref={listRef}>
        {messages.length === 0 && (
          <div className="chat__empty">
            <p>Ask about times, faculty, topics, or what fits your schedule.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" className="suggestion" onClick={() => void send(s)} disabled={busy}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`msg msg--${m.role} ${m.error ? 'msg--error' : ''}`}>
            <div className="msg__bubble">{m.role === 'assistant' ? <Markdown text={m.text} /> : m.text}</div>
            {m.role === 'assistant' && !m.error && (
              <div className="msg__tools">
                {m.tools && m.tools.length > 0 ? (
                  m.tools.map((t) => (
                    <span key={t} className={`tool tool--${t}`}>
                      {TOOL_ICONS[t] ?? '🛠'} {t}
                    </span>
                  ))
                ) : (
                  <span className="tool tool--none">no tools used</span>
                )}
              </div>
            )}
          </div>
        ))}

        {busy && (
          <div className="msg msg--assistant">
            <div className="msg__bubble thinking">
              <span className="dragonball" aria-hidden>
                <span>★</span>
              </span>
              Powering up…
            </div>
          </div>
        )}
      </div>

      <form className="chat__form" onSubmit={onSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask the course agent…"
          rows={2}
          aria-label="Message"
        />
        <button type="submit" className="btn btn--primary" disabled={busy || !input.trim()}>
          {busy ? '…' : 'Send'}
        </button>
      </form>
    </aside>
  )
}
