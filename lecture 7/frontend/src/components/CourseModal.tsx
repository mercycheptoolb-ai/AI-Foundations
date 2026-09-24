import { useEffect } from 'react'
import { displayName, formatDate, sessionLabel, type Course } from '../api'

interface Props {
  course: Course
  onClose: () => void
  onAsk: () => void
}

export default function CourseModal({ course: c, onClose, onAsk }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const start = formatDate(c['Course Session Start date'])
  const end = formatDate(c['Course Session End Date'])
  const syllabus = c.Syllabus || c['Old Syllabus']
  const email = (c['Faculty 1 Email'] ?? '').trim()

  const facts: [string, string][] = [
    ['When', c.Daytimes || 'TBA'],
    ['Session', `${sessionLabel(c['Course Session'])}${start && end ? ` · ${start} – ${end}` : ''}`],
    ['Room', c.Room || 'TBA'],
    ['Units', c.Units || '—'],
    ['Category', [c['Course Category'], c['Course Type']].filter(Boolean).join(' · ') || '—'],
    ['Enrollment', c['Bid Or Permission'] || '—'],
  ]

  return (
    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" onClick={onClose}>
      <div className="modal__panel glass" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal__close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <p className="modal__number">
          {c['Course Number']}
          {c.Section ? ` · Section ${c.Section}` : ''}
        </p>
        <h2 id="modal-title" className="modal__title">
          {c['Course Title']}
        </h2>

        <dl className="facts">
          {facts.map(([k, v]) => (
            <div key={k} className="fact">
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>

        {c['Course Description'] && (
          <section className="modal__section">
            <h4>About the course</h4>
            <p>{c['Course Description']}</p>
          </section>
        )}

        {c['Faculty 1'] && (
          <section className="modal__section">
            <h4>
              Faculty · {displayName(c['Faculty 1'])}
              {email && (
                <a className="modal__link" href={`mailto:${email}`}>
                  {email}
                </a>
              )}
            </h4>
            {c.faculty_bio && <p>{c.faculty_bio}</p>}
          </section>
        )}

        <div className="modal__actions">
          <button type="button" className="btn btn--primary" onClick={onAsk}>
            ⚡ Ask the agent about this course
          </button>
          {syllabus && (
            <a className="btn btn--ghost" href={syllabus} target="_blank" rel="noreferrer">
              Syllabus ↗
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
