// One-off: render HandsomeDan to a static SVG for the README.
import { writeFileSync, mkdirSync } from 'node:fs'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'

const server = await createServer({ server: { middlewareMode: true }, appType: 'custom', logLevel: 'error' })
const { default: HandsomeDan } = await server.ssrLoadModule('/src/components/HandsomeDan.tsx')

const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#4f46e5', '#a855f7']
const size = 120
const gap = 10
const width = colors.length * size + (colors.length - 1) * gap
const dogs = colors
  .map((c, i) =>
    renderToStaticMarkup(React.createElement(HandsomeDan, { furColor: c, size }))
      .replace('<svg ', `<svg x="${i * (size + gap)}" y="0" `)
      .replace(' aria-hidden="true"', ''),
  )
  .join('\n')

const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${size}" width="${width}" height="${size}">\n${dogs}\n</svg>\n`
mkdirSync('../docs', { recursive: true })
writeFileSync('../docs/handsome-dan.svg', svg)
await server.close()
console.log('wrote docs/handsome-dan.svg')
