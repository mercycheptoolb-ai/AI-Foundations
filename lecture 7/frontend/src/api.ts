export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

/** One row of data/yale_som_classes.json, exactly as GET /api/courses returns it. */
export interface Course {
  'Course ID': string
  'Course Number': string
  Section: string
  'Course Title': string
  'Course Description': string
  'Course Category': string
  'Course Type': string
  'Course Session': string
  'Course Session Start date': string
  'Course Session End Date': string
  Daytimes: string
  'Timings Day': string
  'Timings StartTime': string
  'Timings EndTime': string
  Room: string
  Units: string
  'Bid Or Permission': string
  'Faculty 1': string
  'Faculty 1 Email': string
  faculty_bio: string
  Syllabus: string
  'Old Syllabus': string
}

export interface CoursesResponse {
  count: number
  courses: Course[]
}

export interface ChatResponse {
  reply: string
  tools_used: string[]
}

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') return body.detail
    return JSON.stringify(body.detail ?? body)
  } catch {
    return `${res.status} ${res.statusText}`
  }
}

export async function fetchCourses(q: string, signal?: AbortSignal): Promise<CoursesResponse> {
  const url = new URL('/api/courses', API_BASE)
  if (q) url.searchParams.set('q', q)
  const res = await fetch(url, { signal })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

export async function sendChat(message: string): Promise<ChatResponse> {
  const res = await fetch(new URL('/api/chat', API_BASE), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(await readError(res))
  return res.json()
}

// ------------------------------------------------------------------ formatting

const SESSION_LABELS: Record<string, string> = {
  fall: 'Full Fall',
  'fall-1': 'Fall 1',
  'fall-2': 'Fall 2',
}

export function sessionLabel(session: string): string {
  return SESSION_LABELS[session] ?? (session || 'TBA')
}

/** "Simonsohn, Uri" -> "Uri Simonsohn" */
export function displayName(name: string): string {
  const parts = (name ?? '').split(',').map((p) => p.trim())
  return parts.length === 2 && parts[1] ? `${parts[1]} ${parts[0]}` : (name ?? '').trim()
}

/** "20261016 000000.000" -> "Oct 16, 2026" */
export function formatDate(raw: string): string {
  const m = /^(\d{4})(\d{2})(\d{2})/.exec(raw ?? '')
  if (!m) return ''
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function courseKey(c: Course, i: number): string {
  return `${c['Course ID']}-${c.Section}-${i}`
}
