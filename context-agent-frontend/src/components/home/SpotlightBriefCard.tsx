import { Sparkles, ArrowRight, BellPlus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useDigests } from '../../hooks/useDigests'
import { DigestCard } from '../digest/DigestCard'

export function SpotlightBriefCard() {
  const { user, openAuth } = useAuth()
  const { digests, spotlightDigest, isLoading } = useDigests()

  if (!user) {
    return (
      <div className="home-dashboard-card spotlight-empty-card">
        <div className="home-card-header">
          <div className="home-card-title">
            <span className="home-icon-badge blue">
              <Sparkles size={16} />
            </span>
            <div>
              <h3>Daily Topic Briefs</h3>
              <span className="muted text-xs">AI-synthesized news digests</span>
            </div>
          </div>
        </div>

        <div className="spotlight-prompt-body">
          <p className="text-sm muted">
            Sign in to subscribe to keywords (like <strong>ISRO</strong> or <strong>Apple</strong>) and receive automated daily intelligence briefings.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => openAuth('login')}
            style={{ marginTop: '0.75rem' }}
          >
            Log In to Enable Briefs
          </button>
        </div>

        <div className="home-card-footer">
          <span className="muted text-xs">Personalized per user</span>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="home-dashboard-card spotlight-card">
        <div className="empty-state-mini">Loading today's intelligence briefs…</div>
      </div>
    )
  }

  if (!spotlightDigest) {
    return (
      <div className="home-dashboard-card spotlight-empty-card">
        <div className="home-card-header">
          <div className="home-card-title">
            <span className="home-icon-badge blue">
              <Sparkles size={16} />
            </span>
            <div>
              <h3>Spotlight Topic Brief</h3>
              <span className="muted text-xs">From your active subscriptions</span>
            </div>
          </div>
        </div>

        <div className="spotlight-prompt-body">
          <BellPlus size={28} className="text-accent" style={{ margin: '0.5rem auto' }} />
          <h4 style={{ margin: '0.25rem 0' }}>No Topic Watches Yet</h4>
          <p className="text-xs muted">
            Subscribe to up to 5 topics or entities to start receiving daily AI intelligence briefs right here.
          </p>
          <Link to="/watches" className="btn btn-primary btn-sm" style={{ marginTop: '0.75rem' }}>
            + Choose Topics to Track
          </Link>
        </div>

        <div className="home-card-footer">
          <span className="muted text-xs">Generated daily at 6:30 AM</span>
        </div>
      </div>
    )
  }

  return (
    <div className="home-dashboard-card spotlight-card">
      <div className="home-card-header">
        <div className="home-card-title">
          <span className="home-icon-badge blue">
            <Sparkles size={16} />
          </span>
          <div>
            <h3>Today's Spotlight Brief</h3>
            <span className="muted text-xs">1 of {digests.length} active topic briefs</span>
          </div>
        </div>
        <Link to="/briefs" className="home-card-link">
          All Briefs ({digests.length}) <ArrowRight size={13} />
        </Link>
      </div>

      <div className="spotlight-card-body">
        <DigestCard digest={spotlightDigest} isSpotlight={true} />
      </div>

      <div className="home-card-footer">
        <span className="muted text-xs">Synthesized with Gemini AI</span>
        <Link to="/briefs" className="home-footer-link">
          Read All Briefs ({digests.length}) ➔
        </Link>
      </div>
    </div>
  )
}
