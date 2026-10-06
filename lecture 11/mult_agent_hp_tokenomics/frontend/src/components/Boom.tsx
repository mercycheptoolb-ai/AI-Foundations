import { useEffect } from 'react'
import { fmtUsd } from './Thermometer'
import './Boom.css'

const DEBRIS = ['💥', '🔥', '💸', '💵', '🪙', '✨', '💸', '🔥', '💵', '💥', '🪙', '✨', '💸', '💵']

/** Full-screen explosion when the project blows its budget. Click (or wait) to dismiss. */
export function Boom({ spent, budget, onDone }: { spent: number; budget: number; onDone: () => void }) {
  useEffect(() => {
    const t = window.setTimeout(onDone, 4500)
    return () => window.clearTimeout(t)
  }, [onDone])

  return (
    <div className="boom" role="alert" onClick={onDone}>
      <div className="boom-flash" />
      <div className="boom-ring r1" />
      <div className="boom-ring r2" />
      <div className="boom-ring r3" />
      {DEBRIS.map((e, i) => {
        const angle = (i / DEBRIS.length) * Math.PI * 2
        return (
          <span
            key={i}
            className="boom-debris"
            style={{
              ['--dx' as string]: `${Math.cos(angle) * (38 + (i % 3) * 8)}vmax`,
              ['--dy' as string]: `${Math.sin(angle) * (32 + (i % 4) * 6)}vmax`,
              ['--spin' as string]: `${(i % 2 ? 1 : -1) * (360 + i * 40)}deg`,
            }}
          >
            {e}
          </span>
        )
      })}
      <div className="boom-word">BOOM</div>
      <div className="boom-sub">
        Budget blown · {fmtUsd(spent)} of {fmtUsd(budget)}
        <small>all agents stopped · click to dismiss</small>
      </div>
    </div>
  )
}
