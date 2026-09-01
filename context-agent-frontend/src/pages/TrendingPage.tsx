import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { dedupeSearchHits } from '../lib/trendingFilters'
import { TrendingTopicList } from '../components/trending/TrendingTopicList'
import { TrendingArticleList } from '../components/trending/TrendingArticleList'

export function TrendingPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const entityParam = searchParams.get('entity')
  const tabParam = (searchParams.get('tab') as 'news' | 'searches') || 'news'

  const [activeTab, setActiveTab] = useState<'news' | 'searches'>(tabParam)
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(entityParam)

  // Fetch trending list using React Query (cached)
  const { data: trendingData, isLoading: loadingList } = useQuery({
    queryKey: ['trending'],
    queryFn: () => api.getTrending(20),
  })

  const trendingNews = trendingData?.trending_news ?? []
  const trendingSearches = trendingData?.trending_searches ?? []
  const currentList = activeTab === 'news' ? trendingNews : trendingSearches

  // Find the selected entity object from the active list
  const selectedEntity = currentList.find((e) => e.id === selectedEntityId) || null

  // Update activeTab if tabParam changes in URL
  useEffect(() => {
    if (tabParam && (tabParam === 'news' || tabParam === 'searches')) {
      setActiveTab(tabParam)
    }
  }, [tabParam])

  // Select entity from URL query param or fallback to first item in list
  useEffect(() => {
    const list = activeTab === 'news' ? trendingNews : trendingSearches
    if (list.length === 0) {
      setSelectedEntityId(null)
      return
    }

    if (entityParam && list.some((e) => e.id === entityParam)) {
      setSelectedEntityId(entityParam)
    } else if (!selectedEntityId || !list.some((e) => e.id === selectedEntityId)) {
      setSelectedEntityId(list[0].id)
    }
  }, [activeTab, trendingNews, trendingSearches, entityParam, selectedEntityId])

  // Fetch backing articles for selected entity using React Query (cached)
  const { data: articlesData, isLoading: loadingArticles } = useQuery({
    queryKey: ['trendingArticles', selectedEntityId],
    queryFn: () => api.getTrendingArticles(selectedEntityId!),
    enabled: !!selectedEntityId,
  })

  const searchHits = articlesData ? dedupeSearchHits(articlesData.results) : []

  const handleSelectEntity = (entityId: string) => {
    setSelectedEntityId(entityId)
    setSearchParams({ entity: entityId, tab: activeTab })
  }

  const handleTabChange = (tab: 'news' | 'searches') => {
    setActiveTab(tab)
    setSearchParams({ tab })
  }

  return (
    <div className="page trending-page">
      <div className="section-header">
        <h1>Trending Insights</h1>
        <span className="muted">Top canonical entities recognized in articles and user searches</span>
      </div>

      <div className="trending-layout">
        <TrendingTopicList
          activeTab={activeTab}
          onTabChange={handleTabChange}
          topics={currentList}
          selectedEntityId={selectedEntityId || undefined}
          onSelectEntity={(entity) => handleSelectEntity(entity.id)}
          loading={loadingList}
        />

        <TrendingArticleList
          selectedEntityName={selectedEntity?.canonical_name}
          articles={searchHits}
          loading={loadingArticles}
        />
      </div>
    </div>
  )
}
