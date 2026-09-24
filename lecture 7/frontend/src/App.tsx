import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { courseKey, displayName, fetchCourses, type Course } from './api'
import ChatPanel, { type AskRequest } from './components/ChatPanel'
import CourseCard from './components/CourseCard'
import CourseModal from './components/CourseModal'

const SESSIONS = [
  { id: 'all', label: 'All' },
  { id: 'fall', label: 'Full Fall' },
  { id: 'fall-1', label: 'Fall 1' },
  { id: 'fall-2', label: 'Fall 2' },
]

export default function App() {
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const [courses, setCourses] = useState<Course[]>([])
  const [catalogSize, setCatalogSize] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [session, setSession] = useState('all')
  const [selected, setSelected] = useState<Course | null>(null)
  const [ask, setAsk] = useState<AskRequest | null>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 250)
    return () => clearTimeout(t)
  }, [query])

  useEffect(() => {
    const ctrl = new AbortController()
    setLoading(true)
    setError(null)
    fetchCourses(debounced, ctrl.signal)
      .then((data) => {
        setCourses(data.courses)
        if (!debounced) setCatalogSize(data.count)
      })
      .catch((err: unknown) => {
        if (ctrl.signal.aborted) return
        setError(err instanceof Error ? err.message : String(err))
        setCourses([])
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false)
      })
    return () => ctrl.abort()
  }, [debounced])

  const visible = useMemo(
    () => (session === 'all' ? courses : courses.filter((c) => c['Course Session'] === session)),
    [courses, session],
  )

  const facultyCount = useMemo(
    () => new Set(courses.map((c) => c['Faculty 1']).filter(Boolean)).size,
    [courses],
  )

  function askAbout(c: Course) {
    setSelected(null)
    const who = displayName(c['Faculty 1'])
    setAsk({
      id: Date.now(),
      text: `Tell me about ${c['Course Number']} — ${c['Course Title']}${who ? ` (taught by ${who})` : ''}. When does it meet and who is it a good fit for?`,
    })
  }

  return (
    <div className="app">
      <div className="aura aura--orange" aria-hidden />
      <div className="aura aura--blue" aria-hidden />

      <header className="hero glass">
        <div className="hero__brand">
          <span className="hero__ball" aria-hidden>
            ★
          </span>
          <div>
            <h1 className="hero__title">
              SOM Course Explorer <span className="hero__z">Z</span>
            </h1>
            <p className="hero__subtitle">Yale School of Management · Fall catalog · Ask the agent anything</p>
          </div>
        </div>
        <div className="hero__stats">
          <div className="stat">
            <span className="stat__value">{catalogSize ?? '—'}</span>
            <span className="stat__label">courses</span>
          </div>
          <div className="stat">
            <span className="stat__value">{loading ? '…' : visible.length}</span>
            <span className="stat__label">showing</span>
          </div>
          <div className="stat">
            <span className="stat__value">{loading ? '…' : facultyCount}</span>
            <span className="stat__label">faculty</span>
          </div>
        </div>
      </header>

      <div className="layout">
        <main className="catalog">
          <div className="toolbar glass">
            <label className="search">
              <span className="search__icon" aria-hidden>
                ⌕
              </span>
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search titles, faculty, numbers, topics…"
                aria-label="Search courses"
              />
            </label>
            <div className="chips" role="group" aria-label="Filter by session">
              {SESSIONS.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className={`chip ${session === s.id ? 'chip--active' : ''}`}
                  onClick={() => setSession(s.id)}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {error ? (
            <div className="notice glass notice--error">
              <strong>Couldn't reach the backend.</strong> {error}
              <div className="notice__hint">Is it running? From backend/: uvicorn main:app --port 8000</div>
            </div>
          ) : loading && courses.length === 0 ? (
            <div className="grid">
              {Array.from({ length: 6 }, (_, i) => (
                <div key={i} className="card glass card--skeleton" />
              ))}
            </div>
          ) : visible.length === 0 ? (
            <div className="notice glass">No courses match that search. Try fewer words, or ask the agent →</div>
          ) : (
            <div className={`grid ${loading ? 'grid--loading' : ''}`}>
              {visible.map((c, i) => (
                <CourseCard key={courseKey(c, i)} course={c} onOpen={() => setSelected(c)} />
              ))}
            </div>
          )}
        </main>

        <ChatPanel askRequest={ask} />
      </div>

      {selected && <CourseModal course={selected} onClose={() => setSelected(null)} onAsk={() => askAbout(selected)} />}
    </div>
  )
}
