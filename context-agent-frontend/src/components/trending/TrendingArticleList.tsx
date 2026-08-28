import type { SearchHit } from '../../api/types'

interface TrendingArticleListProps {
  selectedEntityName?: string
  articles: SearchHit[]
  loading: boolean
}

export function TrendingArticleList({
  selectedEntityName,
  articles,
  loading,
}: TrendingArticleListProps) {
  return (
    <section className="trending-articles">
      {selectedEntityName && (
        <div className="section-header compact">
          <h2>Coverage Backing:</h2>
          <span className="selected-entity-title">{selectedEntityName}</span>
        </div>
      )}
      {loading ? (
        <div className="empty-state">Loading related articles…</div>
      ) : articles.length ? (
        <div className="search-hit-list">
          {articles.map((hit) => (
            <a
              key={`${hit.article_id}-${hit.url}`}
              className="search-hit"
              href={hit.url}
              target="_blank"
              rel="noreferrer"
            >
              <div className="search-hit-meta">
                <span className="badge">{hit.source}</span>
                {hit.categories.map((cat) => (
                  <span key={cat} className="badge badge-soft">
                    {cat}
                  </span>
                ))}
              </div>
              <h3>{hit.title}</h3>
              <p>{hit.chunk}</p>
            </a>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          {selectedEntityName
            ? `No related articles found for “${selectedEntityName}”.`
            : 'Select a trending entity to view related articles.'}
        </div>
      )}
    </section>
  )
}
