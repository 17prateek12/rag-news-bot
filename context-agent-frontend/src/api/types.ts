export interface Category {
  id: number
  name: string
}

export interface Article {
  id: string
  title: string
  summary: string | null
  url: string
  image_url: string | null
  source: string
  author: string | null
  published_at: string
  categories: string[]
  chunk_count: number
  created_at: string
}

export interface ArticleMetadata {
  pageNo: number
  limit: number | 'all'
  total: number
}

export interface PaginatedArticlesResponse {
  metadata: ArticleMetadata
  articles: Article[]
}

export interface User {
  id: string
  email: string
}

// H-2: After switching to httpOnly cookies, login/register returns the User directly.
// The JWT is set as an httpOnly cookie by the server and never sent in the response body.
export type AuthResponse = User

export interface TrendingEntityResponse {
  id: string
  canonical_name: string
  entity_type: string | null
  rank: number
  score_level: string
}

export interface TrendingResponse {
  window: string
  trending_news: TrendingEntityResponse[]
  trending_searches: TrendingEntityResponse[]
}

export interface SearchHit {
  article_id: string
  title: string
  chunk: string
  source: string
  url: string
  publish_date?: string | null
  categories: string[]
}

export interface HybridSearchResponse {
  query: string
  limit: number
  results: SearchHit[]
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
}

export interface ChatMessage {
  id: string
  role: string
  text: string
  sources?: SourceCitation[]
  created_at: string
}

export interface SourceCitation {
  index: number
  title: string
  source: string
  url: string
  excerpt: string
}

export interface ContextSection {
  key: string
  title: string
  content: string
}

export interface ChatSendResponse {
  session_id: string
  user_message: ChatMessage
  assistant_message: ChatMessage
  intent: string
  intent_confidence: number
  intent_reason: string
  sections: ContextSection[]
  sources: SourceCitation[]
  input_mode: string
  transcript?: string | null
}

export interface ApiError {
  detail?: string
  error?: {
    code?: string
    message?: string
  }
}

export interface Watch {
  id: string
  user_id: string
  keyword: string
  entity_id: string | null
  is_active: boolean
  created_at: string
}

export interface DigestArticle {
  id: string
  title: string
  url: string
  source?: string | null
  published_at?: string | null
}

export interface Digest {
  id: string
  watch_id: string
  keyword: string
  digest_date: string
  summary_text: string
  article_ids: string[]
  articles: DigestArticle[]
  created_at: string
}

export interface PasswordActionResponse {
  message: string
}
