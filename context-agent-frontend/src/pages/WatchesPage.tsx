import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Bell, Check, Flame, Hash, Info, Plus, RotateCcw, Save, Sparkles, Trash2 } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

const MAX_WATCHES = 5

interface StagedWatch {
  id?: string
  keyword: string
  created_at?: string
  isNew?: boolean
}

export function WatchesPage() {
  const { user, openAuth } = useAuth()
  const queryClient = useQueryClient()

  const [keyword, setKeyword] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  // Staged changes (draft state before hitting Save)
  const [stagedAdds, setStagedAdds] = useState<string[]>([])
  const [stagedDeletes, setStagedDeletes] = useState<string[]>([])

  // Fetch active user watches from server
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

  // Compute effective display list (server watches not deleted + newly staged adds)
  const serverActiveWatches: StagedWatch[] = watches
    .filter((w) => !stagedDeletes.includes(w.id))
    .map((w) => ({
      id: w.id,
      keyword: w.keyword,
      created_at: w.created_at,
      isNew: false,
    }))

  const stagedAddWatches: StagedWatch[] = stagedAdds.map((kw) => ({
    keyword: kw,
    isNew: true,
  }))

  const effectiveWatches = [...serverActiveWatches, ...stagedAddWatches]
  const hasChanges = stagedAdds.length > 0 || stagedDeletes.length > 0

  const handleStageAdd = (kwToAdd?: string) => {
    const target = (kwToAdd || keyword).trim()
    if (!target) return
    setErrorMessage('')
    setSuccessMessage('')

    if (effectiveWatches.length >= MAX_WATCHES) {
      setErrorMessage(`You can track a maximum of ${MAX_WATCHES} topics at a time.`)
      return
    }

    const lowerTarget = target.toLowerCase()
    const alreadyTracked = effectiveWatches.some(
      (w) => w.keyword.toLowerCase() === lowerTarget
    )
    if (alreadyTracked) {
      setErrorMessage(`"${target}" is already in your watch list.`)
      return
    }

    // Check if it was previously staged for deletion
    const deletedMatch = watches.find(
      (w) => w.keyword.toLowerCase() === lowerTarget && stagedDeletes.includes(w.id)
    )
    if (deletedMatch) {
      setStagedDeletes((prev) => prev.filter((id) => id !== deletedMatch.id))
    } else {
      setStagedAdds((prev) => [...prev, target])
    }

    setKeyword('')
  }

  const handleStageDelete = (watch: StagedWatch) => {
    setErrorMessage('')
    setSuccessMessage('')

    if (watch.isNew) {
      setStagedAdds((prev) =>
        prev.filter((kw) => kw.toLowerCase() !== watch.keyword.toLowerCase())
      )
    } else if (watch.id) {
      setStagedDeletes((prev) => [...prev, watch.id!])
    }
  }

  const handleCancelChanges = () => {
    setStagedAdds([])
    setStagedDeletes([])
    setErrorMessage('')
    setSuccessMessage('')
    setKeyword('')
  }

  const handleSaveChanges = async () => {
    if (!hasChanges) return
    setIsSaving(true)
    setErrorMessage('')
    setSuccessMessage('')

    try {
      // 1. Process deletions in parallel with Promise.allSettled
      const deletePromises = stagedDeletes.map((id) =>
        api
          .deleteWatch(id)
          .then(() => ({ id, success: true as const }))
          .catch((err) => ({ id, success: false as const, error: err }))
      )

      // 2. Process additions in parallel with Promise.allSettled
      const addPromises = stagedAdds.map((kw) =>
        api
          .createWatch(kw)
          .then(() => ({ keyword: kw, success: true as const }))
          .catch((err) => ({ keyword: kw, success: false as const, error: err }))
      )

      const [deleteResults, addResults] = await Promise.all([
        Promise.all(deletePromises),
        Promise.all(addPromises),
      ])

      const successfulDeleteIds = deleteResults.filter((r) => r.success).map((r) => r.id)
      const failedDeletes = deleteResults.filter((r) => !r.success)

      const successfulAddKeywords = addResults.filter((r) => r.success).map((r) => r.keyword)
      const failedAdds = addResults.filter((r) => !r.success)

      // Reconcile state: clear only the operations that succeeded, keeping failed items staged for retry
      setStagedDeletes((prev) => prev.filter((id) => !successfulDeleteIds.includes(id)))
      setStagedAdds((prev) => prev.filter((kw) => !successfulAddKeywords.includes(kw)))

      if (failedDeletes.length > 0 || failedAdds.length > 0) {
        const errorMessages = [
          ...failedDeletes.map((f) => `Failed to remove topic (${(f as any).error?.message || 'error'})`),
          ...failedAdds.map((f) => `Failed to add "${(f as any).keyword}" (${(f as any).error?.message || 'error'})`),
        ]
        setErrorMessage(`Some changes could not be saved: ${errorMessages.join(', ')}`)
      } else {
        setSuccessMessage(
          'Watch list updated successfully! Your intelligence briefs will be generated in the next scheduled morning cycle and delivered to your feed.'
        )
      }

      await queryClient.invalidateQueries({ queryKey: ['watches'] })
      await queryClient.invalidateQueries({ queryKey: ['digests'] })
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to save changes. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  if (!user) {
    return (
      <div className="page watches-page">
        <div className="empty-state auth-prompt-card">
          <Bell size={48} className="muted" />
          <h2>My Topic Watches</h2>
          <p className="muted">
            Log in to create custom keyword watches and receive daily intelligence digests synthesized by AI.
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
      <div className="watches-container">
        {/* Header */}
        <section className="watches-header-card">
          <div className="watches-header-content">
            <div className="watches-header-icon-wrap">
              <Bell size={24} className="text-accent" />
            </div>
            <div>
              <div className="watches-header-title-row">
                <h2>Topic Watches & Daily Briefs</h2>
                <span className="badge badge-accent watches-quota-badge">
                  {effectiveWatches.length}/{MAX_WATCHES} Topics
                </span>
              </div>
              <p className="muted">
                Track custom topics across global news. Context Agent synthesizes morning intelligence briefs delivered directly to your feed and inbox.
              </p>
            </div>
          </div>
        </section>

        {/* Unsaved Changes Action Banner */}
        {hasChanges && (
          <div className="watches-action-bar">
            <div className="watches-action-info">
              <span className="watches-badge-pending">Unsaved Changes</span>
              <span className="watches-action-text">
                {stagedAdds.length > 0 && `+${stagedAdds.length} new`}
                {stagedAdds.length > 0 && stagedDeletes.length > 0 && ', '}
                {stagedDeletes.length > 0 && `-${stagedDeletes.length} removed`}
              </span>
            </div>
            <div className="watches-action-buttons">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={handleCancelChanges}
                disabled={isSaving}
              >
                <RotateCcw size={14} /> Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={handleSaveChanges}
                disabled={isSaving}
              >
                <Save size={14} /> {isSaving ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </div>
        )}

        {/* Notifications */}
        {errorMessage && (
          <div className="form-error watches-alert" role="alert">
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}
        {successMessage && (
          <div className="form-success watches-alert" role="alert">
            <Check size={16} />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Add Watch Form Card */}
        <section className="watches-form-card">
          <div className="watches-form-header">
            <Sparkles size={18} className="text-accent" />
            <h3>Add Topic to Track</h3>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleStageAdd()
            }}
            className="watches-input-form"
          >
            <div className="watches-input-group">
              <input
                type="text"
                value={keyword}
                onChange={(e) => {
                  setKeyword(e.target.value)
                  if (errorMessage) setErrorMessage('')
                }}
                placeholder="e.g. Artificial Intelligence, ISRO, Apple, Renewable Energy…"
                disabled={effectiveWatches.length >= MAX_WATCHES || isSaving}
                className="watch-input"
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={
                  !keyword.trim() ||
                  effectiveWatches.length >= MAX_WATCHES ||
                  isSaving
                }
              >
                <Plus size={16} /> Add Topic
              </button>
            </div>
          </form>

          {/* Quick-add trending suggestions */}
          {trendingTopics.length > 0 && (
            <div className="watches-suggestions">
              <span className="watches-suggestions-label">
                <Flame size={14} className="text-accent" /> Trending Suggestions:
              </span>
              <div className="watches-pills">
                {trendingTopics.map((topic) => {
                  const isTracked = effectiveWatches.some(
                    (w) => w.keyword.toLowerCase() === topic.toLowerCase()
                  )
                  return (
                    <button
                      key={topic}
                      type="button"
                      className={`trending-suggestion-pill ${isTracked ? 'added' : ''}`}
                      onClick={() => handleStageAdd(topic)}
                      disabled={
                        isTracked ||
                        effectiveWatches.length >= MAX_WATCHES ||
                        isSaving
                      }
                      title={isTracked ? 'Already in watch list' : `Add ${topic}`}
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
          <div className="watches-list-header">
            <h3>
              Your Subscribed Topics ({effectiveWatches.length}/{MAX_WATCHES})
            </h3>
            {hasChanges && (
              <span className="muted watches-hint">
                * Click "Save Changes" above to apply your updates
              </span>
            )}
          </div>

          {loadingWatches ? (
            <div className="empty-state">Loading your watches…</div>
          ) : effectiveWatches.length === 0 ? (
            <div className="empty-state watches-empty">
              <Info size={36} className="muted" />
              <h4>No topics tracked yet</h4>
              <p className="muted">
                Add topics above and click <strong>Save Changes</strong> to generate daily AI intelligence briefs.
              </p>
            </div>
          ) : (
            <div className="watches-grid">
              {effectiveWatches.map((watch) => (
                <div
                  key={watch.id || `staged-${watch.keyword}`}
                  className={`watch-card ${watch.isNew ? 'watch-card-staged-new' : ''}`}
                >
                  <div className="watch-card-info">
                    <div className="watch-card-top-row">
                      <div className="watch-card-tag-icon">
                        <Hash size={14} />
                      </div>
                      <span className="watch-card-keyword">{watch.keyword}</span>
                      {watch.isNew && (
                        <span className="watch-staged-badge">Unsaved</span>
                      )}
                    </div>
                    {watch.created_at ? (
                      <span className="watch-card-date muted">
                        Active since {new Date(watch.created_at).toLocaleDateString()}
                      </span>
                    ) : (
                      <span className="watch-card-date text-accent">
                        Pending scheduled digest
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="icon-btn danger watch-delete-btn"
                    onClick={() => handleStageDelete(watch)}
                    disabled={isSaving}
                    aria-label={`Remove watch for ${watch.keyword}`}
                    title="Remove topic"
                  >
                    <Trash2 size={16} />
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
