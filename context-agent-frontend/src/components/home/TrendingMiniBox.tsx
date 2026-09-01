import { Flame, ArrowUpRight, Zap, Activity } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTrending } from '../../hooks/useTrending'
import type { TrendingEntityResponse } from '../../api/types'

export function TrendingMiniBox() {
  const { trendingNews, isLoading, isError } = useTrending(5)

  const renderStatusBadge = (scoreLevel: string) => {
    const lower = (scoreLevel || '').toLowerCase()

    if (lower === 'hot') {
      return (
        <span className="trending-heat-pill heat-hot">
          <Flame size={12} /> Hot
        </span>
      )
    }

    if (lower === 'warm') {
      return (
        <span className="trending-heat-pill heat-warm">
          <Zap size={12} /> Warm
        </span>
      )
    }

    return (
      <span className="trending-heat-pill heat-active">
        <Activity size={12} /> Active
      </span>
    )
  }

  return (
    <div className="home-dashboard-card trending-mini-box">
      <div className="home-card-header">
        <div className="home-card-title">
          <span className="home-icon-badge orange">
            <Flame size={16} />
          </span>
          <div>
            <h3>Top 5 Trending Now</h3>
            <span className="muted text-xs">Highest mention velocity</span>
          </div>
        </div>
        <Link to="/trending" className="home-card-link">
          View All <ArrowUpRight size={13} />
        </Link>
      </div>

      <div className="trending-mini-list">
        {isLoading ? (
          <div className="empty-state-mini">Loading trending topics…</div>
        ) : isError || trendingNews.length === 0 ? (
          <div className="empty-state-mini">No trending topics detected yet.</div>
        ) : (
          trendingNews.slice(0, 5).map((item: TrendingEntityResponse, idx: number) => (
            <Link
              key={item.id}
              to={`/trending?entity=${encodeURIComponent(item.id)}&tab=news`}
              className="trending-mini-item"
            >
              <div className="trending-mini-left">
                <span className={`trending-rank-badge rank-${idx + 1}`}>{idx + 1}</span>
                <div className="trending-mini-meta">
                  <span className="trending-mini-name">{item.canonical_name}</span>
                  {item.entity_type && (
                    <span className="trending-mini-type">{item.entity_type}</span>
                  )}
                </div>
              </div>

              <div className="trending-mini-right">
                {renderStatusBadge(item.score_level)}
              </div>
            </Link>
          ))
        )}
      </div>

      <div className="home-card-footer">
        <span className="muted text-xs">From Trending Service</span>
        <Link to="/trending" className="home-footer-link">
          Explore Trending Page ➔
        </Link>
      </div>
    </div>
  )
}
