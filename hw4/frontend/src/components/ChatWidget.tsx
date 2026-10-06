import { Fragment, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  clearChatHistory,
  formatPrice,
  getChatHistory,
  sendChat,
  type ChatMessage,
  type ChatProduct,
  type PageContext,
  type PageResults,
} from '../api'
import { reducedMotion } from '../catalog'
import { onOpenChat } from '../chatEvents'
import { useRoster, type Roster } from '../roster'
import { useAuth } from '../useAuth'
import { useChatResults, type ShownResults } from '../useChatResults'
import { stageAttrs, usePhotoStage } from '../usePhotoStage'
import BulldogPatch, { type Mood } from './BulldogPatch'
import RichText from './RichText'

// "Point" at a product's card on the page (chat tile hover, or a fresh reply).
function callCards(ids: string[], ms = 0) {
  document.querySelectorAll<HTMLElement>('.card[data-product-id]').forEach((el) => {
    const on = ids.includes(el.dataset.productId ?? '')
    el.classList.toggle('is-called', on)
    if (on && ms) window.setTimeout(() => el.classList.remove('is-called'), ms)
  })
}

function Tile({ p, number, delay }: { p: ChatProduct; number?: number; delay: number }) {
  const { stage, onLoad } = usePhotoStage(p.image_url)
  return (
    <Link
      to={`/products/${p.product_id}`}
      className="chat-product"
      style={{ animationDelay: `${delay}ms` }}
      onMouseEnter={() => callCards([p.product_id])}
      onMouseLeave={() => callCards([])}
      onFocus={() => callCards([p.product_id])}
      onBlur={() => callCards([])}
    >
      <span className="chat-product-img" {...stageAttrs(stage)}>
        <img src={p.image_url} alt="" loading="lazy" onLoad={onLoad} />
        {number !== undefined && <span className="jersey mini" aria-hidden="true">{String(number).padStart(2, '0')}</span>}
      </span>
      <span className="chat-product-name">{p.name}</span>
      <span className="chat-product-price">{formatPrice(p.price)}</span>
      {p.in_stock_sizes.length === 0 && <span className="chat-product-out">Sold out</span>}
    </Link>
  )
}

function ProductTiles({ products, roster }: { products: ChatProduct[]; roster: Roster | null }) {
  return (
    <div className="chat-products">
      {products.map((p, i) => {
        const n = roster ? roster.items.findIndex((it) => it.id === p.product_id) : -1
        return <Tile key={p.product_id} p={p} number={n >= 0 ? n + 1 : undefined} delay={Math.min(i, 6) * 50} />
      })}
    </div>
  )
}

// "#7" in a shopper's own bubble renders as a little jersey patch.
function withPatches(text: string) {
  return text.split(/(#\d{1,3}\b)/g).map((part, i) =>
    /^#\d{1,3}$/.test(part) ? (
      <span key={i} className="num-patch">{part}</span>
    ) : (
      part
    ),
  )
}

// Problem 8: describe the current page for the agent ("this" = the product on screen).
function pageContext(pathname: string, search: string, results: ShownResults | null): PageContext {
  const path = (pathname + search).slice(0, 200)
  const product = pathname.match(/^\/products\/([a-z0-9-]+)$/)
  if (product) return { path, page_type: 'product', product_id: product[1] }
  if (pathname === '/products') {
    return search.includes('view=chat') && results
      ? { path, page_type: 'chat_results', grid_product_ids: results.products.map((p) => p.product_id).slice(0, 120) }
      : { path, page_type: 'products' }
  }
  const simple: Record<string, PageContext['page_type']> = { '/': 'home', '/about': 'about', '/login': 'login', '/signup': 'signup' }
  return { path, page_type: simple[pathname] ?? 'other' }
}

// Problem 9: one-tap questions that fit the page the shopper is on. With numbered cards on
// screen (Problem 10), the first chips teach "call a number".
function suggestionsFor(page: PageContext, loggedIn: boolean, hasSaved: boolean, rosterSize: number): string[] {
  const numbered = rosterSize >= 2 ? ['Compare #1 and #2', 'Is #1 in stock in M?'] : []
  switch (page.page_type) {
    case 'product':
      return ['Which sizes are in stock?', 'Tell me about this item', 'Show me similar items', 'How much is it?']
    case 'chat_results':
      return [...numbered.slice(0, 1), 'Sort these by price', 'Which of these are in stock in M?', 'Show me something cheaper']
    default:
      // At most 4 chips, so they never crowd out the conversation.
      return [
        ...(loggedIn && hasSaved ? ['What did we talk about last time?'] : []),
        ...numbered.slice(0, 1),
        'What hoodies do you have?',
        'Gift ideas under $50',
        'Show me residential college gear',
        'Navy crewnecks in M',
      ].slice(0, 4)
  }
}

// Remounted (via key in App) whenever the logged-in user changes, so one
// shopper's conversation never carries over to the next.
export default function ChatWidget() {
  const { user, refresh } = useAuth()
  const greeting = user
    ? `Hi ${user.first_name}! I'm the Campus Customs assistant. Your chats are saved to your account, so we can pick up where we left off. Ask me about sizes, colors, or gift ideas.`
    : "Hi! I'm the Campus Customs assistant. Ask me about sizes, colors, or gift ideas. (Log in and I'll remember our chats next time.)"
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [justFound, setJustFound] = useState(0) // products found in the latest reply (mascot "found" mood)
  const [unseen, setUnseen] = useState(0) // score badge on the toggle while the chat is closed
  const [peek, setPeek] = useState(false) // one-time "Need a size? Ask me." pennant
  const endRef = useRef<HTMLDivElement>(null)
  const { roster: rawRoster } = useRoster()
  // False once this widget is replaced (logout / account change). A reply that arrives
  // after that belongs to the previous shopper and must not touch the page.
  const alive = useRef(true)
  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])
  const historyRequested = useRef(false)
  const jumpToEnd = useRef(true) // first scroll after opening is instant, later ones smooth
  const { show, results } = useChatResults()
  const navigate = useNavigate()
  const location = useLocation()
  // Always the current location, even inside an async handler that started earlier.
  const locationRef = useRef(location)
  useEffect(() => {
    locationRef.current = location
  }, [location])

  // Problem 7: put the agent's search results on the page as product cards.
  function showOnPage(results: PageResults) {
    show(results)
    const here = locationRef.current
    if (here.pathname !== '/products' || !here.search.includes('view=chat')) {
      navigate('/products?view=chat')
    }
  }

  // Logged-in shoppers pick up where they left off (fetched once, even if the panel is
  // closed and reopened while the request is still in flight).
  useEffect(() => {
    if (!open || !user || historyLoaded || historyRequested.current) return
    historyRequested.current = true
    getChatHistory()
      .then((past) => {
        if (alive.current) setMessages((current) => [...past, ...current])
      })
      .catch(() => {})
      .finally(() => {
        if (alive.current) setHistoryLoaded(true)
      })
  }, [open, user, historyLoaded])

  useEffect(() => {
    if (open) jumpToEnd.current = true
  }, [open])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: jumpToEnd.current || reducedMotion() ? 'auto' : 'smooth', block: 'end' })
    if (!user || historyLoaded) jumpToEnd.current = false
  }, [messages, open, sending, user, historyLoaded])

  // Opening a product page (from a page card or a chat tile) minimizes the chat so the
  // product isn't hidden behind it. The conversation is kept; the pink button reopens it.
  useEffect(() => {
    if (/^\/products\/[^/]+$/.test(location.pathname)) setOpen(false)
  }, [location.pathname])

  // Only trust the roster for the page it was made on.
  const roster = rawRoster && rawRoster.path === location.pathname ? rawRoster : null

  // Any page can open the chat, and optionally ask a question right away (playbook chips,
  // sold-out rescue, pennants...). sendRef always points at the latest send().
  const sendRef = useRef<(text: string) => boolean>(() => false)
  const queued = useRef<string | null>(null) // a page question asked while a reply was pending
  useEffect(
    () =>
      onOpenChat((prompt) => {
        setOpen(true)
        setPeek(false)
        if (prompt)
          window.setTimeout(() => {
            if (!sendRef.current(prompt)) queued.current = prompt
          }, 0)
        else window.setTimeout(() => inputRef.current?.focus(), 60) // keyboard users land in the chat
      }),
    [],
  )

  // Opening the chat clears the score badge.
  const openRef = useRef(open)
  useEffect(() => {
    openRef.current = open
    if (open) setUnseen(0)
  }, [open])

  // First visit only: the bulldog peeks out with a hint after 8s.
  useEffect(() => {
    if (localStorage.getItem('cc-peeked')) return
    const t = window.setTimeout(() => {
      if (localStorage.getItem('cc-peeked')) return
      localStorage.setItem('cc-peeked', '1') // shown once, ever
      setPeek(true)
    }, 8000)
    return () => window.clearTimeout(t)
  }, [])
  useEffect(() => {
    if (!peek) return
    const t = window.setTimeout(() => setPeek(false), 12000)
    return () => window.clearTimeout(t)
  }, [peek])
  useEffect(() => {
    if (open && peek) setPeek(false)
    if (open) localStorage.setItem('cc-peeked', '1')
  }, [open, peek])

  // The "found" mood lasts 2.5s after a reply with products.
  useEffect(() => {
    if (!justFound) return
    const t = window.setTimeout(() => setJustFound(0), 2500)
    return () => window.clearTimeout(t)
  }, [justFound])

  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (send(input)) setInput('')
  }

  // Returns true if the message was sent (so the typed draft can be cleared).
  function send(raw: string): boolean {
    const text = raw.trim()
    if (!text || sending) return false
    void deliver(text)
    inputRef.current?.focus() // keyboard users keep their place
    return true
  }
  useEffect(() => {
    sendRef.current = send // keep page-triggered questions using the latest state
  })
  useEffect(() => {
    if (!sending && queued.current) {
      const q = queued.current
      queued.current = null
      send(q)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sending])

  // "Call a number": "#7" -> "#7 (Basic Hoodie Big Yale, id basic-hoodie-big-yale)" using the
  // lineup on screen right now. Numbers that aren't on screen are left alone ("#1 fan").
  function expandNumbers(text: string): string {
    const items = roster?.items ?? []
    return text.replace(/(^|[^\w&])#(\d{1,3})\b/g, (m, pre: string, n: string) => {
      const it = items[Number(n) - 1]
      return it ? `${pre}#${n} (${it.name}, id ${it.id})` : m
    })
  }

  async function deliver(typed: string) {
    const text = expandNumbers(typed)
    const history = messages
    const sentFrom = location.key // where the shopper was when they hit Send
    const page = pageContext(location.pathname, location.search, results)
    setMessages((m) => [
      ...m,
      { role: 'user', content: text, display: text !== typed ? typed : undefined, pageProductId: page.product_id },
    ])
    setSending(true)
    try {
      // The server ignores this for logged-in shoppers (it uses saved history), but it
      // keeps context if the session quietly expired.
      const res = await sendChat(text, history, page)
      if (!alive.current) return // the shopper logged out / switched accounts meanwhile
      if (res.logged_in !== Boolean(user)) refresh() // session expired or changed elsewhere
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: res.reply, products: res.products, pageResults: res.page_results },
      ])
      // Closed the chat while waiting? Put the score on the toggle.
      if (!openRef.current) setUnseen(res.page_results?.total_found ?? Math.max(1, res.products.length))
      if (res.products.length) {
        setJustFound(res.page_results?.total_found ?? res.products.length)
        // Point at the matching cards already on the page (twice-pulsing glow).
        window.setTimeout(() => callCards(res.products.map((p) => p.product_id), 2400), 60)
      }
      if (res.page_results) {
        if (locationRef.current.key === sentFrom) {
          showOnPage(res.page_results)
          // On a phone the open chat would cover the whole grid, so step aside (and keep
          // the score on the toggle so they know where the results came from).
          if (window.matchMedia('(max-width: 760px)').matches) {
            setOpen(false)
            setUnseen(res.page_results.total_found)
          }
        } else {
          // They moved on (e.g. opened a product) while waiting: don't yank them away.
          // The results are still one tap away via the "on the page" button.
          show(res.page_results)
        }
      }
    } catch (err) {
      if (!alive.current) return
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: (err as Error).message || 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      if (alive.current) setSending(false)
    }
  }

  async function handleClear() {
    if (!window.confirm('Delete your saved chat history? This can’t be undone.')) return
    try {
      await clearChatHistory()
      if (alive.current) setMessages([])
    } catch (err) {
      refresh() // e.g. 401: the session ended in another tab
      if (alive.current) setMessages((m) => [...m, { role: 'assistant', content: (err as Error).message }])
    }
  }

  const savedCount = messages.filter((m) => m.saved).length
  const suggestions = suggestionsFor(
    pageContext(location.pathname, location.search, results),
    Boolean(user),
    savedCount > 0,
    roster?.items.length ?? 0,
  )
  const mood: Mood = sending ? 'thinking' : justFound ? 'found' : 'idle'
  const status =
    mood === 'thinking' ? 'Looking that up…' : mood === 'found' ? `Found ${justFound} for you` : 'Sizes · colors · styles'

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" id="cc-chat-panel" aria-label="Shopping assistant">
          <header className="chat-header">
            <div className="chat-title">
              <span className="chat-avatar">
                <BulldogPatch mood={mood} size={26} />
              </span>
              <span>
                <strong>Bulldog Assistant</strong>
                <span className="chat-status">{status}</span>
                <span className="sr-only" aria-live="polite">{mood === 'idle' ? '' : status}</span>
              </span>
            </div>
            <div className="chat-header-actions">
              {user && messages.length > 0 && !sending && (
                <button className="chat-clear" onClick={handleClear} title="Delete your saved chat history">
                  Clear history
                </button>
              )}
              <button onClick={() => setOpen(false)} aria-label="Close chat">
                ×
              </button>
            </div>
          </header>
          <div className="chat-messages" aria-live="polite">
            {savedCount > 0 && <div className="chat-divider">Your earlier chats</div>}
            {savedCount === 0 && <div className="bubble assistant">{greeting}</div>}
            {messages.map((m, i) => (
              <Fragment key={i}>
                <div className={`msg ${m.role}`}>
                  <div className={`bubble ${m.role}`}>
                    {m.role === 'assistant' ? <RichText text={m.content} /> : withPatches(m.display ?? m.content.replace(/, id [a-z0-9-]+\)/g, ')'))}
                  </div>
                  {m.products && m.products.length > 0 && <ProductTiles products={m.products} roster={roster} />}
                  {m.pageResults && (
                    <button className="chat-page-link" onClick={() => showOnPage(m.pageResults!)}>
                      ▦ {m.pageResults.title}: {m.pageResults.total_found} on the page
                    </button>
                  )}
                </div>
                {m.saved && i === savedCount - 1 && (
                  <>
                    <div className="chat-divider">Now</div>
                    <div className="bubble assistant">Welcome back, {user?.first_name}! What can I help you find today?</div>
                  </>
                )}
              </Fragment>
            ))}
            {sending && (
              <div className="bubble assistant typing" aria-label="Assistant is typing">
                <span />
                <span />
                <span />
              </div>
            )}
            <div ref={endRef} />
          </div>
          <div className="chat-suggestions" role="group" aria-label="Suggested questions" aria-busy={sending}>
            {suggestions.map((q) => (
              <button key={q} type="button" className="chip-btn" onClick={() => send(q)} disabled={sending}>
                {q}
              </button>
            ))}
          </div>
          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a product, or a #number…"
              aria-label="Chat message"
              maxLength={1000}
            />
            <button type="submit" disabled={sending || !input.trim()}>
              Send
            </button>
          </form>
        </section>
      )}
      {peek && !open && (
        <button
          type="button"
          className="peek-pennant"
          onClick={() => {
            setPeek(false)
            setOpen(true)
          }}
        >
          Need a size? Ask me.
        </button>
      )}
      <button
        className={`chat-toggle${open ? ' is-open' : ''}`}
        aria-expanded={open}
        aria-controls="cc-chat-panel"
        title={!open && unseen > 0 ? `${unseen} new result${unseen === 1 ? '' : 's'}` : undefined}
        onClick={() => {
          setOpen((o) => !o)
          setPeek(false)
          localStorage.setItem('cc-peeked', '1')
        }}
        aria-label={!open && unseen > 0 ? `Toggle chat (${unseen} new result${unseen === 1 ? '' : 's'})` : 'Toggle chat'}
      >
        {open ? <span className="toggle-x" aria-hidden="true">×</span> : <BulldogPatch mood={mood} size={40} />}
        {!open && unseen > 0 && (
          <span className="chat-badge" aria-hidden="true">
            {unseen > 99 ? '99' : unseen}
          </span>
        )}
      </button>
    </div>
  )
}
