/** Original stylized Handsome Dan bulldog mascot — a chubby, happy bulldog in a
 * Yale-blue bandana. Coat color is a prop so each course card can get its own dog. */

interface HandsomeDanProps {
  /** Main coat color. */
  furColor?: string
  /** Bandana color (defaults to Yale blue). */
  bandanaColor?: string
  /** Rendered width/height in px. */
  size?: number
  className?: string
}

/** Mixes a hex color toward white (positive amt) or black (negative amt), amt in [-1, 1]. */
function shade(hex: string, amt: number): string {
  const num = parseInt(hex.replace('#', ''), 16)
  const channels = [(num >> 16) & 0xff, (num >> 8) & 0xff, num & 0xff]
  const mixed = channels.map((c) => {
    const target = amt >= 0 ? 255 : 0
    const v = Math.round(c + (target - c) * Math.abs(amt))
    return Math.min(255, Math.max(0, v))
  })
  return `#${mixed.map((v) => v.toString(16).padStart(2, '0')).join('')}`
}

export default function HandsomeDan({
  furColor = '#f97316',
  bandanaColor = '#00356b',
  size = 64,
  className,
}: HandsomeDanProps) {
  const light = shade(furColor, 0.4)
  const dark = shade(furColor, -0.25)
  const bandanaDark = shade(bandanaColor, -0.2)
  const ink = '#2b2320'

  return (
    <svg
      viewBox="0 0 100 120"
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
    >
      {/* chubby round belly */}
      <ellipse cx="50" cy="102" rx="44" ry="30" fill={furColor} />

      {/* stubby front paws */}
      <ellipse cx="29" cy="117" rx="10" ry="6" fill={light} />
      <ellipse cx="71" cy="117" rx="10" ry="6" fill={light} />

      {/* ears (behind head) — short, flopped-down bulldog ears */}
      <path d="M13 27 q-4 17 10 27 q7 2 9 -5 q-4 -12 -3 -25 q-8 -4 -16 3 Z" fill={dark} />
      <path d="M87 27 q4 17 -10 27 q-7 2 -9 -5 q4 -12 3 -25 q8 -4 16 3 Z" fill={dark} />

      {/* head — wide, round and chubby */}
      <ellipse cx="50" cy="42" rx="36" ry="27" fill={furColor} />

      {/* muzzle + big round chubby cheeks (jowls) */}
      <ellipse cx="50" cy="57" rx="24" ry="14" fill={light} />
      <ellipse cx="32" cy="70" rx="14.5" ry="16.5" fill={light} />
      <ellipse cx="68" cy="70" rx="14.5" ry="16.5" fill={light} />

      {/* forehead wrinkles */}
      <path d="M31 23 q19 -6 38 0" stroke={dark} strokeWidth="1.5" fill="none" opacity="0.4" strokeLinecap="round" />
      <path d="M29 31 q21 -5 42 0" stroke={dark} strokeWidth="1.5" fill="none" opacity="0.3" strokeLinecap="round" />

      {/* happy closed eyes */}
      <path d="M32 36 q5 -7 10 0" stroke={ink} strokeWidth="2.5" fill="none" strokeLinecap="round" />
      <path d="M58 36 q5 -7 10 0" stroke={ink} strokeWidth="2.5" fill="none" strokeLinecap="round" />

      {/* nose — broad and flat */}
      <ellipse cx="50" cy="51" rx="9.5" ry="6.5" fill={ink} />
      <ellipse cx="46.4" cy="51" rx="1.4" ry="2" fill="#000" opacity="0.55" />
      <ellipse cx="53.6" cy="51" rx="1.4" ry="2" fill="#000" opacity="0.55" />

      {/* mouth + smile */}
      <path d="M50 57.5 v4.5" stroke={ink} strokeWidth="1.8" strokeLinecap="round" />
      <path d="M50 62 q-10 8 -18 3" stroke={ink} strokeWidth="1.8" fill="none" strokeLinecap="round" />
      <path d="M50 62 q10 8 17 3" stroke={ink} strokeWidth="1.8" fill="none" strokeLinecap="round" />

      {/* tongue */}
      <path
        d="M52.5 62 q4.5 10 -0.5 17 q-6 3 -8 -4 q-0.5 -8 8.5 -13 Z"
        fill="#e8899f"
        stroke="#c96a83"
        strokeWidth="0.6"
      />

      {/* bandana */}
      <path d="M24 80 L76 80 L50 106 Z" fill={bandanaColor} stroke={bandanaDark} strokeWidth="1" />
      <path d="M24 80 q26 10 52 0" fill="none" stroke={bandanaDark} strokeWidth="1" opacity="0.55" />
      <text
        x="50"
        y="99"
        textAnchor="middle"
        fontFamily="Georgia, 'Libre Baskerville', serif"
        fontWeight={700}
        fontSize="14"
        fill="#ffffff"
      >
        Y
      </text>
    </svg>
  )
}
