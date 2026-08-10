import type { SearchHit, TrendingQuery } from '../api/types'

const MAX_TRENDING_QUERY_LEN = 120
const MAX_TRENDING_WORDS = 15

const BLOCKLIST = [
  /^test\b/,
  /\btest chat\b/,
  /\btest query\b/,
  /^nonsense\b/,
  /xyzabc/,
  /^foo\b/,
  /^bar\b/,
  /^asdf\b/,
  /^hello\b/,
  /^hi\b/,
  /zorbax/,
  /\b[a-f0-9]{6,}\b/,
  /\bwelcome to the\b/,
  /\bhere's your host\b/,
  /\btoday, we're talking\b/,
  /\bmade by google podcast\b/,
  /\bdevices getting\b/,
  /\bmade by google\b/,
  /\bpixel feature\b/,
]

export function isTrendingWorthyQuery(query: string) {
  const normalized = query.trim().toLowerCase().replace(/\s+/g, ' ')
  if (normalized.length < 3 || normalized.length > MAX_TRENDING_QUERY_LEN) return false

  const words = normalized.split(' ')
  if (words.length > MAX_TRENDING_WORDS) return false
  if (BLOCKLIST.some((pattern) => pattern.test(normalized))) return false

  const sentenceMarkers = normalized.match(/[.!?]/g)
  if (sentenceMarkers && sentenceMarkers.length >= 2) return false

  return true
}

export function filterTrendingQueries(queries: TrendingQuery[]) {
  return queries.filter(
    (item) =>
      isTrendingWorthyQuery(item.query) &&
      isTrendingWorthyQuery(item.topic) &&
      Boolean(item.topic?.trim()),
  )
}

export function truncateTrendingLabel(query: string, maxLen = 80) {
  const normalized = query.trim().replace(/\s+/g, ' ')
  if (normalized.length <= maxLen) return normalized
  return `${normalized.slice(0, maxLen - 1).trimEnd()}…`
}

export function dedupeSearchHits(hits: SearchHit[]) {
  const seen = new Set<string>()
  return hits.filter((hit) => {
    if (seen.has(hit.article_id)) return false
    seen.add(hit.article_id)
    return true
  })
}
