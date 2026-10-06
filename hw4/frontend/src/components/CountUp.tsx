import { useEffect, useState } from 'react'
import { reducedMotion } from '../catalog'

// Scoreboard digits that roll from 00 to the value (decorative; real text lives elsewhere).
export default function CountUp({ value, digits = 2, ms = 700 }: { value: number; digits?: number; ms?: number }) {
  const [n, setN] = useState(reducedMotion() ? value : 0)
  useEffect(() => {
    if (reducedMotion()) {
      setN(value)
      return
    }
    let raf = 0
    const start = performance.now()
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / ms)
      setN(Math.round(value * (1 - Math.pow(1 - k, 3)))) // easeOutCubic
      if (k < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value, ms])
  return <>{String(n).padStart(digits, '0')}</>
}
