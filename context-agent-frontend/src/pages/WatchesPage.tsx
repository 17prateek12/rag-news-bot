import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Flame, Info, Plus, Trash2 } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const MAX_WATCHES = 5

export function WatchesPage() {
  const { user, openAuth } = useAuth()
  const queryClient = useQueryClient()

  const [keyword, setKeyword] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  // Fetch active user watches
  const { data: watches = [], isLoading: loadingWatches } = useQuery({
    queryKey: ['watches'],
    queryFn: () => api.listWatches(),
    enabled: !!user,
  })

  // Fetch trending topics for quick-add suggestions
  const { data: trendingData } = useQuery({
    queryKey: ['trending'],
    queryFn: () => api.getTrending(12),
  })

  const trendingTopics = (trendingData?.trending_news ?? [])
    .slice(0, 8)
    .map((t) => t.canonical_name)

  // Create watch mutation
  const createMutation = useMutation({
    mutationFn: (kw: string) => api.createWatch(kw),
    onSuccess: () => {
      setKeyword('')
      setErrorMessage('')
      queryClient.invalidateQueries({ queryKey: ['watches'] })
    },
    onError: (err: Error) => {
      setErrorMessage(err.message || 'Failed to create watch')
    },
  })

  // Delete watch mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteWatch(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watches'] })
      queryClient.invalidateQueries({ queryKey: ['digests'] })
    },
  })

  const handleAddWatch = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = keyword.trim()
    if (!trimmed) return
    if (watches.length >= MAX_WATCHES) {
      setErrorMessage(`Maximum limit of ${MAX_WATCHES} watches reached.`)
      return
    }
    createMutation.mutate(trimmed)
  }

  const handleQuickAdd = (topic: string) => {
    if (!user) {
      openAuth('login')
      return
    }
    if (watches.some((w) => w.keyword.toLowerCase() === topic.toLowerCase())) {
      return
    }
    if (watches.length >= MAX_WATCHES) {
      setErrorMessage(`Maximum limit of ${MAX_WATCHES} watches reached.`)
      return
    }
    createMutation.mutate(topic)
  }

  if (!user) {
    return (
      <div className="page watches-page">
        <div className="empty-state auth-prompt-card">
          <Bell size={48} className="muted" />
          <h2>My Topic Watches</h2>
          <p className="muted">
            Log in to create custom keyword watches and receive daily intelligence digests.
          </p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => openAuth('login')}
          >
            Log in to get started
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page watches-page">
      <div className="section-header">
        <div className="watches-title-wrap">
          <h1>My Topic Watches</h1>
          <span className="badge badge-accent watches-counter">
            {watches.length} / {MAX_WATCHES} watches used
          </span>
        </div>
        <p className="muted">
          Subscribe to keywords, entities, or companies. Once a day, our system finds all
          relevant news and generates a concise daily brief on your Home feed.
        </p>
      </div>

      <div className="watches-layout">
        {/* Watch Creation Form */}
        <section className="watches-form-card">
          <h3>Add New Watch</h3>
          <form onSubmit={handleAddWatch} className="watches-input-form">
            <div className="watches-input-group">
              <input
                type="text"
                className="input"
                placeholder="e.g. ISRO, Semiconductor, RBI, Apple..."
                value={keyword}
                onChange={(e) => {
                  setKeyword(e.target.value)
                  if (errorMessage) setErrorMessage('')
                }}
                disabled={watches.length >= MAX_WATCHES || createMutation.isPending}
                maxLength={100}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={
                  !keyword.trim() ||
                  watches.length >= MAX_WATCHES ||
                  createMutation.isPending
                }
              >
                <Plus size={18} /> Add Watch
              </button>
            </div>

            {errorMessage && <div className="form-error">{errorMessage}</div>}
          </form>

          {/* Quick Suggestions from Trending */}
          {trendingTopics.length > 0 && (
            <div className="watches-suggestions">
              <span className="watches-suggestions-label">
                <Flame size={14} /> Suggested Trending Entities:
              </span>
              <div className="watches-pills">
                {trendingTopics.map((topic) => {
                  const isTracked = watches.some(
                    (w) => w.keyword.toLowerCase() === topic.toLowerCase()
                  )
                  return (
                    <button
                      key={topic}
                      type="button"
                      className={`pill ${isTracked ? 'pill-active' : ''}`}
                      disabled={isTracked || watches.length >= MAX_WATCHES}
                      onClick={() => handleQuickAdd(topic)}
                    >
                      {topic} {isTracked ? '✓' : '+'}
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </section>

        {/* Active Watches List */}
        <section className="watches-list-section">
          <h3>Active Subscriptions ({watches.length})</h3>

          {loadingWatches ? (
            <div className="empty-state">Loading your watches…</div>
          ) : watches.length === 0 ? (
            <div className="empty-state watches-empty">
              <Info size={32} className="muted" />
              <p>You haven't set up any topic watches yet.</p>
              <span className="muted">
                Add a topic above to receive customized daily morning briefings.
              </span>
            </div>
          ) : (
            <div className="watches-grid">
              {watches.map((w) => (
                <div key={w.id} className="watch-card">
                  <div className="watch-card-info">
                    <span className="watch-card-keyword">{w.keyword}</span>
                    <span className="watch-card-date muted">
                      Added on {new Date(w.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="icon-btn text-danger watch-delete-btn"
                    title={`Delete watch for ${w.keyword}`}
                    onClick={() => deleteMutation.mutate(w.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
