import type { ReactNode } from 'react'

const INLINE = /(\*\*[^*]+\*\*|\[[^\]]+\]\([^)\s]+\)|`[^`]+`)/g
const LINK = /^\[([^\]]+)\]\(([^)\s]+)\)$/
const LIST_ITEM = /^\s*(?:[-*•]|\d+\.)\s+/

function renderInline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  let i = 0
  let m: RegExpExecArray | null
  INLINE.lastIndex = 0
  while ((m = INLINE.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const tok = m[0]
    const key = `${keyBase}-${i++}`
    if (tok.startsWith('**')) {
      out.push(<strong key={key}>{tok.slice(2, -2)}</strong>)
    } else if (tok.startsWith('`')) {
      out.push(<code key={key}>{tok.slice(1, -1)}</code>)
    } else {
      const link = LINK.exec(tok)
      if (link && /^https?:\/\//.test(link[2])) {
        out.push(
          <a key={key} href={link[2]} target="_blank" rel="noreferrer">
            {link[1]}
          </a>,
        )
      } else {
        out.push(tok)
      }
    }
    last = m.index + tok.length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

/** Tiny, safe markdown renderer for agent replies (bold, code, links, lists, headings). */
export default function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let list: string[] = []

  const flush = () => {
    if (list.length === 0) return
    const k = `ul-${blocks.length}`
    blocks.push(
      <ul key={k}>
        {list.map((item, i) => (
          <li key={i}>{renderInline(item, `${k}-${i}`)}</li>
        ))}
      </ul>,
    )
    list = []
  }

  for (const line of text.split('\n')) {
    if (LIST_ITEM.test(line)) {
      list.push(line.replace(LIST_ITEM, ''))
      continue
    }
    flush()
    const trimmed = line.trim()
    if (!trimmed) continue
    const k = `p-${blocks.length}`
    const heading = /^#{1,6}\s+(.*)$/.exec(trimmed)
    blocks.push(
      heading ? (
        <p key={k} className="md-heading">
          {renderInline(heading[1], k)}
        </p>
      ) : (
        <p key={k}>{renderInline(trimmed, k)}</p>
      ),
    )
  }
  flush()

  return <div className="md">{blocks}</div>
}
