import { useState } from 'react'
import { Bell, Sparkles, BellPlus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useDigests } from '../hooks/useDigests'
import { DigestCard } from '../components/digest/DigestCard'
import { BriefDetailModal } from '../components/digest/BriefDetailModal'
import type { Digest } from '../api/types'

export function BriefsPage() {
  const { user, openAuth } = useAuth()
  const { digests, isLoading } = useDigests(14)
  const [selectedBrief, setSelectedBrief] = useState<Digest | null>(null)

  if (!user) {
    return (
      <div className="page briefs-page">
        <div className="auth-prompt-card">
          <Sparkles size={40} className="text-accent" />
          <h2>Topic Intelligence Briefs</h2>
          <p className="muted">
            Sign in to access your automated AI daily briefs for tracked topics and entities.
          </p>
          <button type="button" className="btn btn-primary" onClick={() => openAuth('login')}>
            Log in to View Briefs
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page briefs-page">
      <section className="hero" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={24} className="text-accent" />
              <h1>All Topic Briefs</h1>
            </div>
            <p className="muted">
              AI-synthesized daily intelligence summaries for all your active topic subscriptions.
            </p>
          </div>
          <Link to="/watches" className="btn btn-primary btn-sm">
            <Bell size={15} /> Manage Watches
          </Link>
        </div>
      </section>

      {isLoading ? (
        <div className="empty-state">Loading your intelligence briefs…</div>
      ) : digests.length === 0 ? (
        <div className="watches-empty">
          <BellPlus size={36} className="text-accent" />
          <h3>No Briefs Generated Yet</h3>
          <p className="muted">
            You don't have any daily briefs generated yet. Make sure you are subscribed to topics in My Watches.
          </p>
          <Link to="/watches" className="btn btn-primary" style={{ marginTop: '0.5rem' }}>
            + Subscribe to Topics
          </Link>
        </div>
      ) : (
        <div className="compact-briefs-grid">
          {digests.map((d) => (
            <DigestCard key={d.id} digest={d} onOpenModal={(digest) => setSelectedBrief(digest)} />
          ))}
        </div>
      )}

      {/* Shared Detail Modal */}
      {selectedBrief && (
        <BriefDetailModal digest={selectedBrief} onClose={() => setSelectedBrief(null)} />
      )}
    </div>
  )
}
