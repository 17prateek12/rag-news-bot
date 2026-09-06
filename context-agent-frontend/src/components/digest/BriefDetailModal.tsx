import { X, ExternalLink, Newspaper, Calendar, Sparkles } from 'lucide-react'
import type { Digest, DigestArticle } from '../../api/types'

interface BriefDetailModalProps {
  digest: Digest | null
  onClose: () => void
}

export function BriefDetailModal({ digest, onClose }: BriefDetailModalProps) {
  if (!digest) return null

  // Render formatted summary with full detail
  const renderFullSummary = (digest: Digest) => {
    if (digest.overview || (digest.bullets && digest.bullets.length > 0)) {
      return (
        <>
          {digest.overview && <p className="digest-modal-paragraph">{digest.overview}</p>}
          {digest.bullets && digest.bullets.length > 0 && (
            <>
              <h4 className="digest-modal-section-title">Key Updates & Findings</h4>
              <ul className="digest-modal-bullets-list">
                {digest.bullets.map((bullet, idx) => (
                  <li key={idx} className="digest-modal-bullet">
                    {bullet}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      )
    }

    const text = digest.summary_text || ''
    const lines = text.split('\n').map((l) => l.trim()).filter((l) => l.length > 0)
    const headerPatterns = [
      'key updates',
      'key findings',
      'key takeaways',
      'key developments',
      'highlights',
      'bullet points',
      'updates:',
      'summary:',
    ]

    return lines.map((line, idx) => {
      const lower = line.toLowerCase()
      if (headerPatterns.some((hp) => lower.startsWith(hp))) {
        return (
          <h4 key={idx} className="digest-modal-section-title">
            Key Updates & Findings
          </h4>
        )
      }
      const bulletMatch = line.match(/^(?:[-*•]|\d+[\.\)])\s*(.+)$/)
      if (bulletMatch) {
        return (
          <li key={idx} className="digest-modal-bullet">
            {bulletMatch[1].trim()}
          </li>
        )
      }
      return (
        <p key={idx} className="digest-modal-paragraph">
          {line}
        </p>
      )
    })
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card digest-detail-modal" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          className="icon-btn modal-close"
          onClick={onClose}
          aria-label="Close"
        >
          <X size={20} />
        </button>

        {/* Modal Header */}
        <div className="digest-modal-header">
          <div className="digest-modal-badge-row">
            <span className="badge badge-accent digest-modal-topic-badge">
              <Sparkles size={13} /> {digest.keyword}
            </span>
            <span className="digest-modal-date">
              <Calendar size={13} /> {digest.digest_date}
            </span>
          </div>
          <h2 className="digest-modal-title">Daily Intelligence Brief</h2>
          <span className="text-xs muted">Synthesized across verified news sources using Gemini AI</span>
        </div>

        {/* Modal Body */}
        <div className="digest-modal-body">
          <div className="digest-modal-summary">
            {renderFullSummary(digest)}
          </div>

          {digest.articles && digest.articles.length > 0 && (
            <div className="digest-modal-sources-section">
              <div className="digest-modal-sources-header">
                <Newspaper size={16} className="text-accent" />
                <h3>Verified Sources & Citations ({digest.articles.length})</h3>
              </div>
              <div className="digest-modal-sources-list">
                {digest.articles.map((art: DigestArticle) => (
                  <a
                    key={art.id}
                    href={art.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="digest-modal-source-item"
                  >
                    <div className="source-item-meta">
                      <span className="source-item-publisher">{art.source || 'News Source'}</span>
                      {art.published_at && (
                        <span className="source-item-date">
                          {new Date(art.published_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <div className="source-item-title-row">
                      <h4 className="source-item-title">{art.title}</h4>
                      <ExternalLink size={14} className="source-item-icon" />
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="digest-modal-footer">
          <button type="button" className="btn btn-secondary btn-full" onClick={onClose}>
            Close Brief
          </button>
        </div>
      </div>
    </div>
  )
}
