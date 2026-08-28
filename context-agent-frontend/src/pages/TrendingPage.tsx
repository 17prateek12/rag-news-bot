import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { dedupeSearchHits } from '../lib/trendingFilters'
import { TrendingTopicList } from '../components/trending/TrendingTopicList'
import { TrendingArticleList } from '../components/trending/TrendingArticleList'

export function TrendingPage() {
  const [activeTab, setActiveTab] = useState<'news' | 'searches'>('news')
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)

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

  // Auto-select first item when active tab changes or trending list loads
  useEffect(() => {
    const list = activeTab === 'news' ? trendingNews : trendingSearches
    if (list.length > 0) {
      setSelectedEntityId(list[0].id)
    } else {
      setSelectedEntityId(null)
    }
  }, [activeTab, trendingNews, trendingSearches])

  // Fetch backing articles for selected entity using React Query (cached)
  const { data: articlesData, isLoading: loadingArticles } = useQuery({
    queryKey: ['trendingArticles', selectedEntityId],
    queryFn: () => api.getTrendingArticles(selectedEntityId!),
    enabled: !!selectedEntityId,
  })

  const searchHits = articlesData ? dedupeSearchHits(articlesData.results) : []

  return (
    <div className="page trending-page">
      <div className="section-header">
        <h1>Trending Insights</h1>
        <span className="muted">Top canonical entities recognized in articles and user searches</span>
      </div>

      <div className="trending-layout">
        <TrendingTopicList
          activeTab={activeTab}
          onTabChange={setActiveTab}
          topics={currentList}
          selectedEntityId={selectedEntityId || undefined}
          onSelectEntity={(entity) => setSelectedEntityId(entity.id)}
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
