// A hanging varsity jersey (decorative SVG): name arched across the shoulders and a
// chenille-textured number. Used in the home hero and on the sign-up page.
export default function Jersey({ name = 'CUSTOMS', number = '57', className = '' }: { name?: string; number?: string; className?: string }) {
  const label =
    (name || 'CUSTOMS')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // José -> JOSE
      .toUpperCase()
      .replace(/[^A-Z0-9 .'-]/g, '')
      .slice(0, 12) || 'CUSTOMS'
  const nameSize = Math.min(22, (22 * 8) / label.length) // long names shrink to fit the shoulders
  return (
    <svg className={`jersey-svg ${className}`} viewBox="0 0 240 260" aria-hidden="true">
      <defs>
        <pattern id="mesh" width="6" height="6" patternUnits="userSpaceOnUse">
          <rect width="6" height="6" fill="#141416" />
          <circle cx="3" cy="3" r="1.1" fill="#1d1d20" />
        </pattern>
        <filter id="chenille" x="-10%" y="-10%" width="120%" height="120%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.5" />
        </filter>
        <path id="shoulders" d="M 52 92 Q 120 58 188 92" />
      </defs>
      {/* hanger */}
      <path d="M120 6 q 10 0 10 10 q 0 8 -10 12 l 0 6" fill="none" stroke="#a8a3a0" strokeWidth="3" strokeLinecap="round" />
      <path d="M58 40 L120 32 L182 40" fill="none" stroke="#a8a3a0" strokeWidth="3" strokeLinecap="round" />
      {/* body */}
      <path
        d="M78 36 Q120 58 162 36 L214 62 L232 118 L196 128 L192 252 L48 252 L44 128 L8 118 L26 62 Z"
        fill="url(#mesh)"
        stroke="#2b2b30"
        strokeWidth="2"
      />
      {/* pink trim: collar + sleeve hems */}
      <path d="M78 36 Q120 62 162 36" fill="none" stroke="#ff4fa3" strokeWidth="6" strokeLinecap="round" />
      <path d="M232 118 L196 128" stroke="#ff4fa3" strokeWidth="6" strokeLinecap="round" />
      <path d="M8 118 L44 128" stroke="#ff4fa3" strokeWidth="6" strokeLinecap="round" />
      <text className="jersey-name" fontSize={nameSize} fill="#f6f3ef" textAnchor="middle">
        <textPath href="#shoulders" startOffset="50%">{label}</textPath>
      </text>
      <text
        className="jersey-number"
        x="120"
        y="214"
        fontSize="112"
        textAnchor="middle"
        fill="#ff4fa3"
        stroke="#f6f3ef"
        strokeWidth="3"
        paintOrder="stroke"
        filter="url(#chenille)"
      >
        {number}
      </text>
    </svg>
  )
}
