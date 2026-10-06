import type { Product } from './api'

export function matchesText(p: Product, q: string) {
  if (!q) return true
  return [p.name, p.garment_type, p.description, ...p.colors, ...p.search_tags].join(' ').toLowerCase().includes(q)
}

export const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
