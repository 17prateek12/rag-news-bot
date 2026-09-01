import type {
  ApiError,
  AuthResponse,
  Category,
  ChatMessage,
  ChatSendResponse,
  ChatSession,
  Digest,
  HybridSearchResponse,
  PaginatedArticlesResponse,
  PasswordActionResponse,
  TrendingResponse,
  User,
  Watch,
} from './types'

export const API_BASE =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? '/api' : '')

// H-2: All requests use credentials: 'include' so the browser automatically sends
// the httpOnly 'access_token' cookie set by the server on login/register.
// The token is never stored in localStorage or accessible to JavaScript.
async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include', // H-2: always send cookies (httpOnly access_token)
  })

  if (!response.ok) {
    let message = response.statusText
    try {
      const body = (await response.json()) as ApiError
      message = body.error?.message ?? body.detail ?? message
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

  // H-2: login and register return the User directly; the JWT is set as an httpOnly cookie by the server
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

  // H-2: Logout clears the httpOnly cookie on the server side
  logout: () =>
    request<void>('/auth/logout', { method: 'POST' }),

  me: () => request<User>('/auth/me'),

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

  listChatSessions: () => request<ChatSession[]>('/chat/sessions'),
  createChatSession: (title?: string) =>
    request<ChatSession>(
      '/chat/sessions',
      { method: 'POST', body: JSON.stringify({ title: title ?? null }) },
    ),
  listChatMessages: (sessionId: string) =>
    request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),
  sendChatMessage: (sessionId: string, query: string, limit = 6) =>
    request<ChatSendResponse>(
      `/chat/sessions/${sessionId}/messages`,
      { method: 'POST', body: JSON.stringify({ query, limit }) },
    ),
  sendVoiceMessage: (sessionId: string, audio: Blob, filename: string, limit = 6) => {
    const form = new FormData()
    form.append('audio', audio, filename)
    form.append('limit', String(limit))
    return request<ChatSendResponse>(
      `/chat/sessions/${sessionId}/messages/audio`,
      { method: 'POST', body: form },
    )
  },
  deleteChatSession: (sessionId: string) =>
    request<void>(`/chat/sessions/${sessionId}`, { method: 'DELETE' }),

  listWatches: () => request<Watch[]>('/watches'),
  createWatch: (keyword: string) =>
    request<Watch>(
      '/watches',
      { method: 'POST', body: JSON.stringify({ keyword }) },
    ),
  deleteWatch: (watchId: string) =>
    request<void>(`/watches/${watchId}`, { method: 'DELETE' }),

  listDigests: () => request<Digest[]>('/digests'),

  forgotPassword: (email: string) =>
    request<PasswordActionResponse>(
      '/auth/forgot-password',
      { method: 'POST', body: JSON.stringify({ email }) },
    ),
  resetPassword: (token: string, new_password: string) =>
    request<PasswordActionResponse>(
      '/auth/reset-password',
      { method: 'POST', body: JSON.stringify({ token, new_password }) },
    ),
  changePassword: (current_password: string, new_password: string) =>
    request<PasswordActionResponse>(
      '/auth/change-password',
      { method: 'POST', body: JSON.stringify({ current_password, new_password }) },
    ),
}
