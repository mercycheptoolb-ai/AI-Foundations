import { displayName, sessionLabel, type Course } from '../api'

interface Props {
  course: Course
  onOpen: () => void
}

export default function CourseCard({ course: c, onOpen }: Props) {
  const session = c['Course Session']
  return (
    <button type="button" className="card glass" onClick={onOpen}>
      <div className="card__top">
        <span className="card__number">{c['Course Number']}</span>
        <span className={`badge badge--${session || 'tba'}`}>{sessionLabel(session)}</span>
      </div>
      <h3 className="card__title">{c['Course Title']}</h3>
      {c['Faculty 1'] && <p className="card__faculty">{displayName(c['Faculty 1'])}</p>}
      <p className="card__desc">{c['Course Description'] || 'No description provided.'}</p>
      <div className="card__meta">
        {c.Daytimes && <span className="meta">🕒 {c.Daytimes}</span>}
        {c['Course Category'] && <span className="meta meta--cat">{c['Course Category']}</span>}
        {c.Units && <span className="meta">{c.Units} units</span>}
      </div>
    </button>
  )
}
