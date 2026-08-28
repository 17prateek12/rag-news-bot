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
import type { TrendingEntityResponse } from '../../api/types'

interface TrendingTopicListProps {
  activeTab: 'news' | 'searches'
  onTabChange: (tab: 'news' | 'searches') => void
  topics: TrendingEntityResponse[]
  selectedEntityId?: string
  onSelectEntity: (entity: TrendingEntityResponse) => void
  loading: boolean
}

export function TrendingTopicList({
  activeTab,
  onTabChange,
  topics,
  selectedEntityId,
  onSelectEntity,
  loading,
}: TrendingTopicListProps) {
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

  return (
    <aside className="trending-topics">
      {/* Tabs */}
      <div className="trending-tabs" style={{ marginBottom: '16px' }}>
        <button
          type="button"
          className={`tab-btn${activeTab === 'news' ? ' active' : ''}`}
          onClick={() => onTabChange('news')}
        >
          <Flame size={16} />
          Trending News
        </button>
        <button
          type="button"
          className={`tab-btn${activeTab === 'searches' ? ' active' : ''}`}
          onClick={() => onTabChange('searches')}
        >
          <TrendingUp size={16} />
          Trending Searches
        </button>
      </div>

      {loading && <div className="empty-state">Loading entities…</div>}
      {!loading && !topics.length && (
        <div className="empty-state">No trending entities detected yet.</div>
      )}
      <div className="trending-topic-list-container">
        {topics.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`trending-topic${selectedEntityId === item.id ? ' active' : ''}`}
            onClick={() => onSelectEntity(item)}
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
      </div>
    </aside>
  )
}
