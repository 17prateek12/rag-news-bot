import type {
  ApiError,
  PaginatedArticlesResponse,
  AuthResponse,
  Category,
  ChatMessage,
  ChatSendResponse,
  ChatSession,
  HybridSearchResponse,
  TrendingResponse,
  User,
} from './types'

export const API_BASE =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? '/api' : '')

const TOKEN_KEY = 'context_agent_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = false,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (auth) {
    const token = getToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    let message = response.statusText
    try {
      const body = (await response.json()) as ApiError
      message = body.error?.message ?? message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  listCategories: () => request<Category[]>('/categories'),
  listArticles: (pageNo?: number, limit?: number | 'all', category?: string) => {
    const params = new URLSearchParams()
    if (pageNo !== undefined) params.append('pageNo', String(pageNo))
    if (limit !== undefined) params.append('limit', String(limit))
    if (category) params.append('category', category)
    const qs = params.toString()
    return request<PaginatedArticlesResponse>(qs ? `/articles?${qs}` : '/articles')
  },

  register: (email: string, password: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>('/auth/me', {}, true),

  hybridSearch: (q: string, limit = 8, topicMatch = false) =>
    request<HybridSearchResponse>(
      `/search/hybrid?q=${encodeURIComponent(q)}&limit=${limit}&rerank=true&topic_match=${topicMatch}`,
    ),

  bm25Search: (q: string, limit = 12) =>
    request<HybridSearchResponse>(
      `/search/bm25?q=${encodeURIComponent(q)}&limit=${limit}`,
    ),

  getTrending: (limit = 15) => request<TrendingResponse>(`/trending?limit=${limit}`),
  getTrendingArticles: (entityId: string) =>
    request<HybridSearchResponse>(`/trending/entities/${entityId}/articles`),

  listChatSessions: () => request<ChatSession[]>('/chat/sessions', {}, true),
  createChatSession: (title?: string) =>
    request<ChatSession>(
      '/chat/sessions',
      { method: 'POST', body: JSON.stringify({ title: title ?? null }) },
      true,
    ),
  listChatMessages: (sessionId: string) =>
    request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`, {}, true),
  sendChatMessage: (sessionId: string, query: string, limit = 6) =>
    request<ChatSendResponse>(
      `/chat/sessions/${sessionId}/messages`,
      { method: 'POST', body: JSON.stringify({ query, limit }) },
      true,
    ),
  sendVoiceMessage: (sessionId: string, audio: Blob, filename: string, limit = 6) => {
    const form = new FormData()
    form.append('audio', audio, filename)
    form.append('limit', String(limit))
    return request<ChatSendResponse>(
      `/chat/sessions/${sessionId}/messages/audio`,
      { method: 'POST', body: form },
      true,
    )
  },
  deleteChatSession: (sessionId: string) =>
    request<void>(`/chat/sessions/${sessionId}`, { method: 'DELETE' }, true),
}
