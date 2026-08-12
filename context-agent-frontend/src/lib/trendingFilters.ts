import type { SearchHit } from '../api/types'

export function dedupeSearchHits(hits: SearchHit[]) {
  const seen = new Set<string>()
  return hits.filter((hit) => {
    if (seen.has(hit.article_id)) return false
    seen.add(hit.article_id)
    return true
  })
}
