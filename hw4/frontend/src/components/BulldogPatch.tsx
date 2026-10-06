// The Bulldog Assistant's face: a stitched chenille patch built from plain HTML spans
// (project rule: creatures are HTML, not images). A generic cartoon bulldog, not a logo.
export type Mood = 'idle' | 'thinking' | 'found'

export default function BulldogPatch({ mood = 'idle', size = 38 }: { mood?: Mood; size?: number }) {
  return (
    <span className={`bulldog mood-${mood}`} style={{ fontSize: size }} aria-hidden="true">
      <span className="bd-head">
        <span className="bd-ear left" />
        <span className="bd-ear right" />
        <span className="bd-eye left" />
        <span className="bd-eye right" />
        <span className="bd-muzzle">
          <span className="bd-nose" />
          <span className="bd-tooth left" />
          <span className="bd-tooth right" />
        </span>
      </span>
    </span>
  )
}
