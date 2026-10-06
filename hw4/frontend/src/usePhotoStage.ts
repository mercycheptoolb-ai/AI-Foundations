import { useCallback, useEffect, useState, type CSSProperties, type SyntheticEvent } from 'react'

// Product photos come three ways: garment on black, garment on white, and white photos
// with black side bars baked in. This looks at each photo once and picks a matching
// "stage": dark photos sit on pure black, white photos multiply onto warm paper, and
// baked-in side bars are clipped away. Results are cached per image.
export interface PhotoStage {
  stage: 'light' | 'dark'
  barL: number // % to clip from the left (letterboxed photos)
  barR: number
}

const cache = new Map<string, PhotoStage>()
const DARK: PhotoStage = { stage: 'dark', barL: 0, barR: 0 }

function analyze(img: HTMLImageElement): PhotoStage {
  try {
    const N = 128
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = N
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!
    ctx.drawImage(img, 0, 0, N, N)
    const px = ctx.getImageData(0, 0, N, N).data
    const lum = (x: number, y: number) => {
      const i = (y * N + x) * 4
      return 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]
    }
    const corner = (lum(1, 1) + lum(N - 2, 1) + lum(1, N - 2) + lum(N - 2, N - 2)) / 4
    if (corner > 200) return { stage: 'light', barL: 0, barR: 0 }
    if (corner < 40) {
      // Letterboxed? A white band across the top and bottom rows, black at the sides.
      const run = (y: number) => {
        let first = -1, last = -1
        for (let x = 0; x < N; x++) if (lum(x, y) > 235) { if (first < 0) first = x; last = x }
        return { first, last }
      }
      const a = run(2), b = run(N - 3)
      const square = Math.abs(img.naturalWidth - img.naturalHeight) / img.naturalWidth < 0.02
      if (a.first >= 0 && b.first >= 0 && a.last - a.first > 38 && b.last - b.first > 38 &&
          Math.abs(a.first - b.first) <= 2 && Math.abs(a.last - b.last) <= 2) {
        return {
          stage: 'light',
          // +0.3% inward so the bar edge disappears without shaving sleeve tips
          barL: square ? (Math.min(a.first, b.first) / N) * 100 + 0.3 : 0,
          barR: square ? ((N - 1 - Math.max(a.last, b.last)) / N) * 100 + 0.3 : 0,
        }
      }
    }
    return DARK
  } catch {
    return DARK
  }
}

// Returns the stage (null until known) and an onLoad handler for the product <img>.
// Analysing the element the page already loads keeps the browser's lazy loading working.
export function usePhotoStage(src: string): { stage: PhotoStage | null; onLoad: (e: SyntheticEvent<HTMLImageElement>) => void } {
  const [stage, setStage] = useState<PhotoStage | null>(() => cache.get(src) ?? null)
  useEffect(() => {
    setStage(cache.get(src) ?? null)
  }, [src])
  const onLoad = useCallback(
    (e: SyntheticEvent<HTMLImageElement>) => {
      let s = cache.get(src)
      if (!s) {
        s = analyze(e.currentTarget)
        cache.set(src, s)
      }
      setStage(s)
    },
    [src],
  )
  return { stage, onLoad }
}

export function stageAttrs(s: PhotoStage | null): { 'data-stage': string; style: CSSProperties } {
  return {
    'data-stage': s?.stage ?? 'pending',
    style: { '--bar-l': `${s?.barL ?? 0}%`, '--bar-r': `${s?.barR ?? 0}%` } as CSSProperties,
  }
}
