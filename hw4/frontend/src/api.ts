// Thin client for the FastAPI backend (backend/main.py).
// In dev, Vite proxies /api and /images to http://127.0.0.1:8000.

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  total_stock?: number
  category?: string | null
  stock_by_size?: Record<string, number>
}

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends Product {
  sizes: SizeStock[]
}

// Product tile under an assistant reply (built by the backend from the database).
export interface ChatProduct {
  product_id: string
  name: string
  garment_type: string
  price: number
  image_url: string
  colors: string[]
  in_stock_sizes: string[]
  short_description: string
}

// Problem 7 contract: when the shopper asks about a type of item, the chat reply also
// carries every matching product for the website to show as a grid on the page.
export interface PageResults {
  title: string
  search: Record<string, unknown>
  total_found: number
  products: ChatProduct[]
}

export interface ChatResponse {
  reply: string
  products: ChatProduct[]
  page_results?: PageResults | null
  logged_in: boolean // did the server see a logged-in session (and save this exchange)?
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: ChatProduct[]
  pageResults?: PageResults | null
  saved?: boolean // loaded from the shopper's saved history
  pageProductId?: string // (user turns) product page they sent it from
  display?: string // (user turns) what the shopper typed, if "#7" was expanded for the agent
}

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const UNREACHABLE = 'Can’t reach the server right now. Please try again in a moment.'

// FastAPI errors look like {"detail": "..."} or, for validation, {"detail": [{msg}, ...]}.
async function errorMessage(res: Response): Promise<string> {
  if (res.status === 404) return 'Not found'
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg
  } catch {
    // Non-JSON body, e.g. the Vite proxy's 502 when the backend isn't running.
  }
  return res.status >= 500 ? UNREACHABLE : `Request failed (${res.status})`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    // Same-origin requests send the HttpOnly session cookie automatically.
    res = await fetch(path, { credentials: 'same-origin', ...init })
  } catch {
    throw new ApiError(0, UNREACHABLE)
  }
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res))
  return res.json() as Promise<T>
}

const postJson = <T>(path: string, body?: unknown) =>
  request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

export interface SignupInput {
  first_name: string
  last_name: string
  email: string
  password: string
}

export const signup = (input: SignupInput) => postJson<{ user: User }>('/api/auth/signup', input)

export const login = (email: string, password: string) =>
  postJson<{ user: User }>('/api/auth/login', { email, password })

export const logout = () => postJson<{ ok: boolean }>('/api/auth/logout')

export async function getCurrentUser(): Promise<User | null> {
  try {
    return (await request<{ user: User }>('/api/auth/me')).user
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return null
    throw e
  }
}

export const getProducts = () => request<Product[]>('/api/products')

// One shared request for the product list (ticker, home, pennants, products page).
let productsPromise: Promise<Product[]> | null = null
export function getProductsCached(): Promise<Product[]> {
  productsPromise ??= getProducts().catch((e) => {
    productsPromise = null // let the next caller retry
    throw e
  })
  return productsPromise
}

export const getProduct = (id: string) =>
  request<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)

// Problem 8: where the shopper is, sent with every chat message so the agent knows
// which product "this" means. Only ids are sent; the server looks up the names.
export interface PageContext {
  path: string
  page_type: 'home' | 'products' | 'chat_results' | 'product' | 'about' | 'login' | 'signup' | 'other'
  product_id?: string
  grid_product_ids?: string[]
}

// Guests send the conversation so far (logged-in history is kept by the server).
export const sendChat = (message: string, history: ChatMessage[] = [], page?: PageContext) =>
  postJson<ChatResponse>('/api/chat', {
    message,
    page,
    history: history.slice(-20).map((m) => ({
      role: m.role,
      content: m.content.slice(0, 4000),
      product_ids: (m.products ?? []).slice(0, 6).map((p) => p.product_id),
      page_product_id: m.pageProductId,
    })),
  })

interface HistoryMessage {
  role: 'user' | 'assistant'
  content: string
  products: ChatProduct[]
  page_results: PageResults | null
  created_at: string
}

export const getChatHistory = async (): Promise<ChatMessage[]> =>
  (await request<HistoryMessage[]>('/api/chat/history')).map((m) => ({
    role: m.role,
    content: m.content,
    products: m.products,
    pageResults: m.page_results,
    saved: true,
  }))

export const clearChatHistory = () =>
  request<{ deleted: number }>('/api/chat/history', { method: 'DELETE' })

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

export const shortText = (text: string, max = 90) =>
  text.length <= max ? text : `${text.slice(0, text.lastIndexOf(' ', max))}…`
