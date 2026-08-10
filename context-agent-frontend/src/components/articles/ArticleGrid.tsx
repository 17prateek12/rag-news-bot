import type { Article } from '../../api/types'
import { ArticleCard } from './ArticleCard'

interface ArticleGridProps {
  articles: Article[]
  emptyMessage?: string
}

export function ArticleGrid({ articles, emptyMessage = 'No articles found.' }: ArticleGridProps) {
  if (!articles.length) {
    return <div className="empty-state">{emptyMessage}</div>
  }
  return (
    <div className="article-grid">
      {articles.map((article) => (
        <ArticleCard key={article.id} article={article} />
      ))}
    </div>
  )
}
