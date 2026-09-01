import { Newspaper, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useCategoryHighlights } from '../../hooks/useCategoryHighlights'

export function CategoryHighlights() {
  const { articles, totalCount, isLoading, isError } = useCategoryHighlights(4)

  const formatTimeAgo = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diffHrs = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
      if (diffHrs < 1) return 'Just now'
      if (diffHrs === 1) return '1h ago'
      if (diffHrs < 24) return `${diffHrs}h ago`
      const diffDays = Math.floor(diffHrs / 24)
      return `${diffDays}d ago`
    } catch {
      return ''
    }
  }

  return (
    <div className="home-dashboard-card category-highlights-card">
      <div className="home-card-header">
        <div className="home-card-title">
          <span className="home-icon-badge green">
            <Newspaper size={16} />
          </span>
          <div>
            <h3>Category Highlights</h3>
            <span className="muted text-xs">Fresh top stories across desks</span>
          </div>
        </div>
        <Link to="/articles" className="home-card-link">
          All News <ArrowRight size={13} />
        </Link>
      </div>

      <div className="category-highlights-list">
        {isLoading ? (
          <div className="empty-state-mini">Loading fresh stories…</div>
        ) : isError || articles.length === 0 ? (
          <div className="empty-state-mini">No recent articles available yet.</div>
        ) : (
          articles.map((art) => {
            const categoryName = art.categories && art.categories.length > 0 ? art.categories[0] : 'General'
            return (
              <a
                key={art.id}
                href={art.url}
                target="_blank"
                rel="noopener noreferrer"
                className="category-highlight-item"
              >
                <div className="highlight-item-header">
                  <span className="highlight-category-pill">{categoryName}</span>
                  <span className="highlight-time muted">{formatTimeAgo(art.published_at)}</span>
                </div>
                <h4 className="highlight-title">{art.title}</h4>
              </a>
            )
          })
        )}
      </div>

      <div className="home-card-footer">
        <span className="muted text-xs">{totalCount} stories indexed</span>
        <Link to="/articles" className="home-footer-link">
          View All Categories ➔
        </Link>
      </div>
    </div>
  )
}
