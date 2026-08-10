import type { Article } from '../../api/types'
import { formatRelative, truncate } from '../../lib/format'

interface ArticleCardProps {
  article: Article
}

export function ArticleCard({ article }: ArticleCardProps) {
  return (
    <a className="article-card" href={article.url} target="_blank" rel="noreferrer">
      <div className="article-card-image">
        {article.image_url ? (
          <img src={article.image_url} alt="" loading="lazy" />
        ) : (
          <div className="article-card-placeholder" />
        )}
      </div>
      <div className="article-card-body">
        <div className="article-card-meta">
          <span className="badge">{article.source}</span>
          {article.categories.slice(0, 2).map((cat) => (
            <span key={cat} className="badge badge-soft">
              {cat}
            </span>
          ))}
        </div>
        <h3>{article.title}</h3>
        <p>{truncate(article.summary ?? 'No summary available.', 160)}</p>
        <span className="article-card-time">{formatRelative(article.published_at)}</span>
      </div>
    </a>
  )
}
