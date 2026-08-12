import { useEffect, useState } from 'react'
import {
  User as UserIcon,
  Building2,
  MapPin,
  Calendar,
  Cpu,
  HelpCircle,
  Flame,
  TrendingUp,
} from 'lucide-react'
import { api } from '../api/client'
import type { SearchHit, TrendingEntityResponse } from '../api/types'
import { dedupeSearchHits } from '../lib/trendingFilters'

export function TrendingPage() {
  const [activeTab, setActiveTab] = useState<'news' | 'searches'>('news')
  const [trendingNews, setTrendingNews] = useState<TrendingEntityResponse[]>([])
  const [trendingSearches, setTrendingSearches] = useState<TrendingEntityResponse[]>([])
  const [selectedEntity, setSelectedEntity] = useState<TrendingEntityResponse | null>(null)
  const [searchHits, setSearchHits] = useState<SearchHit[]>([])
  
  const [loadingList, setLoadingList] = useState(true)
  const [loadingArticles, setLoadingArticles] = useState(false)

  // Fetch trending entities on mount
  useEffect(() => {
    ;(async () => {
      setLoadingList(true)
      try {
        const res = await api.getTrending(20)
        setTrendingNews(res.trending_news)
        setTrendingSearches(res.trending_searches)
        
        // Auto-select first item of the active tab
        const defaultEntity = res.trending_news[0] ?? null
        setSelectedEntity(defaultEntity)
      } catch (err) {
        console.error('Failed to fetch trending topics', err)
      } finally {
        setLoadingList(false)
      }
    })()
  }, [])

  // Auto-select first item when active tab changes
  useEffect(() => {
    const list = activeTab === 'news' ? trendingNews : trendingSearches
    setSelectedEntity(list[0] ?? null)
  }, [activeTab, trendingNews, trendingSearches])

  // Fetch articles when selected entity changes
  useEffect(() => {
    if (!selectedEntity) {
      setSearchHits([])
      return
    }
    let cancelled = false
    ;(async () => {
      setLoadingArticles(true)
      try {
        const search = await api.getTrendingArticles(selectedEntity.id)
        if (cancelled) return
        setSearchHits(dedupeSearchHits(search.results))
      } catch (err) {
        console.error('Failed to fetch articles for entity', err)
        if (!cancelled) setSearchHits([])
      } finally {
        if (!cancelled) setLoadingArticles(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [selectedEntity])

  // Helper to render type badge
  const renderTypeBadge = (type: string | null) => {
    if (!type) return null
    const lower = type.toLowerCase()
    
    let icon = <HelpCircle size={12} />
    let label = 'Other'
    let className = 'badge-other'

    if (lower === 'person') {
      icon = <UserIcon size={12} />
      label = 'Person'
      className = 'badge-person'
    } else if (lower === 'organization') {
      icon = <Building2 size={12} />
      label = 'Org'
      className = 'badge-org'
    } else if (lower === 'location') {
      icon = <MapPin size={12} />
      label = 'Location'
      className = 'badge-loc'
    } else if (lower === 'event') {
      icon = <Calendar size={12} />
      label = 'Event'
      className = 'badge-event'
    } else if (lower === 'technology') {
      icon = <Cpu size={12} />
      label = 'Tech'
      className = 'badge-tech'
    }

    return (
      <span className={`entity-type-badge ${className}`}>
        {icon}
        {label}
      </span>
    )
  }

  // Helper to render heat level badge
  const renderHeatBadge = (level: string) => {
    const lower = level.toLowerCase()
    let className = 'heat-active'
    let label = 'Active'

    if (lower === 'hot') {
      className = 'heat-hot'
      label = 'Hot'
    } else if (lower === 'warm') {
      className = 'heat-warm'
      label = 'Warm'
    }

    return (
      <span className={`entity-heat-badge ${className}`}>
        {lower === 'hot' && <Flame size={12} className="flame-icon" />}
        {label}
      </span>
    )
  }

  const currentList = activeTab === 'news' ? trendingNews : trendingSearches

  return (
    <div className="page trending-page">
      <div className="section-header">
        <h1>Trending Insights</h1>
        <span className="muted">Top canonical entities recognized in articles and user searches</span>
      </div>

      {/* Tabs */}
      <div className="trending-tabs">
        <button
          type="button"
          className={`tab-btn${activeTab === 'news' ? ' active' : ''}`}
          onClick={() => setActiveTab('news')}
        >
          <Flame size={16} />
          Trending News
        </button>
        <button
          type="button"
          className={`tab-btn${activeTab === 'searches' ? ' active' : ''}`}
          onClick={() => setActiveTab('searches')}
        >
          <TrendingUp size={16} />
          Trending Searches
        </button>
      </div>

      <div className="trending-layout">
        <aside className="trending-topics">
          {loadingList && <div className="empty-state">Loading entities…</div>}
          {!loadingList && !currentList.length && (
            <div className="empty-state">No trending entities detected yet.</div>
          )}
          {currentList.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`trending-topic${selectedEntity?.id === item.id ? ' active' : ''}`}
              onClick={() => setSelectedEntity(item)}
            >
              <div className="topic-left">
                <span className="trending-rank">#{item.rank}</span>
                <div className="topic-text-group">
                  <span className="trending-topic-text">{item.canonical_name}</span>
                  <div className="topic-badges">
                    {renderTypeBadge(item.entity_type)}
                    {renderHeatBadge(item.score_level)}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </aside>

        <section className="trending-articles">
          {selectedEntity && (
            <div className="section-header compact">
              <h2>Coverage Backing:</h2>
              <span className="selected-entity-title">{selectedEntity.canonical_name}</span>
            </div>
          )}
          {loadingArticles ? (
            <div className="empty-state">Loading related articles…</div>
          ) : searchHits.length ? (
            <div className="search-hit-list">
              {searchHits.map((hit) => (
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
              {selectedEntity
                ? `No related articles found for “${selectedEntity.canonical_name}”.`
                : 'Select a trending entity to view related articles.'}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
