import './Thermometer.css'

export interface ThermometerProps {
  /** Dollars spent so far. */
  value: number
  /** Dollars that fill the tube to the top. */
  max: number
  size?: 'sm' | 'lg'
  accent?: string
  label?: string
  title?: string
}

/** Cheap dollars need more digits to show up at all. */
export function fmtUsd(v: number): string {
  if (v === 0) return '$0'
  if (v < 0.01) return `$${v.toFixed(5)}`
  if (v < 1) return `$${v.toFixed(4)}`
  return `$${v.toFixed(2)}`
}

/** Glass thermometer whose mercury rises with spend. */
export function Thermometer({ value, max, size = 'sm', accent = '#ff4da6', label, title }: ThermometerProps) {
  const ratio = max > 0 ? value / max : 0
  // Any spend at all shows a sliver, so a $0.0004 call still registers.
  const pct = value > 0 ? Math.max(Math.min(ratio, 1) * 100, 3) : 0
  const heat = ratio >= 1 ? 'over' : ratio >= 0.75 ? 'hot' : ratio >= 0.4 ? 'warm' : 'cool'
  const ticks = size === 'lg' ? [0.25, 0.5, 0.75] : []

  return (
    <div
      className={`thermo ${size} ${heat}`}
      style={{ ['--accent' as string]: accent }}
      title={title ?? `${fmtUsd(value)} of ${fmtUsd(max)}`}
      role="meter"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      aria-label={label ?? 'Spend'}
    >
      {size === 'lg' && <div className="thermo-readout">{fmtUsd(value)}</div>}
      <div className="thermo-tube">
        <div className="thermo-mercury" style={{ height: `${pct}%` }} />
        {ticks.map((t) => (
          <span key={t} className="thermo-tick" style={{ bottom: `${t * 100}%` }}>
            <em>{fmtUsd(max * t)}</em>
          </span>
        ))}
      </div>
      <div className="thermo-bulb" />
      {size === 'lg' && (
        <div className="thermo-caption">
          {label}
          <span>{Math.round(ratio * 100)}% of {fmtUsd(max)}</span>
        </div>
      )}
      {size === 'sm' && <div className="thermo-mini">{fmtUsd(value)}</div>}
    </div>
  )
}
