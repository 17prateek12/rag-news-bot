import { useState } from 'react'
import { ExternalLink, Newspaper, Maximize2 } from 'lucide-react'
import type { Digest, DigestArticle } from '../../api/types'
import { BriefDetailModal } from './BriefDetailModal'

interface DigestCardProps {
  digest: Digest
  isSpotlight?: boolean
  onOpenModal?: (digest: Digest) => void
}

export function DigestCard({ digest, isSpotlight = false, onOpenModal }: DigestCardProps) {
  const [modalOpen, setModalOpen] = useState(false)

  const handleOpen = () => {
    if (onOpenModal) {
      onOpenModal(digest)
    } else {
      setModalOpen(true)
    }
  }

  // Parse text into executive paragraph and bullet points
  const parseSummaryContent = (text: string) => {
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
    const paragraphs: string[] = []
    const bullets: string[] = []

    for (const line of lines) {
      if (line.startsWith('- ') || line.startsWith('* ')) {
        bullets.push(line.substring(2))
      } else if (!line.toLowerCase().startsWith('key updates:')) {
        paragraphs.push(line)
      }
    }

    return {
      paragraph: paragraphs.join(' '),
      bullets,
    }
  }

  const { paragraph, bullets } = parseSummaryContent(digest.summary_text)
  const visibleSources = digest.articles ? digest.articles.slice(0, 2) : []
  const remainingSourcesCount = digest.articles ? Math.max(0, digest.articles.length - 2) : 0

  return (
    <>
      <article className={`compact-digest-card ${isSpotlight ? 'spotlight-variant' : ''}`}>
        {/* Card Header */}
        <div className="compact-card-header">
          <div className="compact-badge-group">
            <span className="badge badge-accent compact-topic-badge">{digest.keyword}</span>
            {isSpotlight && <span className="compact-spotlight-tag">SPOTLIGHT</span>}
          </div>
          <span className="compact-card-date muted">{digest.digest_date}</span>
        </div>

        {/* Card Body with Clamped Content */}
        <div className="compact-card-body">
          {paragraph && <p className="compact-summary-text">{paragraph}</p>}

          {bullets.length > 0 && (
            <div className="compact-bullets-box">
              <span className="compact-bullets-label">Key Highlights:</span>
              <ul className="compact-bullets-list">
                {bullets.slice(0, 2).map((bullet, idx) => (
                  <li key={idx} className="compact-bullet-item">
                    {bullet}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Compact Sources Footer */}
        <div className="compact-card-footer">
          {digest.articles && digest.articles.length > 0 && (
            <div className="compact-sources-row">
              <span className="compact-sources-label">
                <Newspaper size={12} /> Sources:
              </span>
              <div className="compact-source-chips">
                {visibleSources.map((art: DigestArticle) => (
                  <a
                    key={art.id}
                    href={art.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="compact-source-chip"
                    title={art.title}
                  >
                    <span className="compact-chip-text">{art.source || 'News'}</span>
                    <ExternalLink size={10} />
                  </a>
                ))}
                {remainingSourcesCount > 0 && (
                  <button
                    type="button"
                    className="compact-more-sources-btn"
                    onClick={handleOpen}
                    title="View all source citations"
                  >
                    +{remainingSourcesCount} more
                  </button>
                )}
              </div>
            </div>
          )}

          <button
            type="button"
            className="compact-expand-btn"
            onClick={handleOpen}
            aria-label="View full brief"
          >
            <span>Full Brief & Sources</span>
            <Maximize2 size={12} />
          </button>
        </div>
      </article>

      {/* Internal Modal fallback if not managed by parent */}
      {!onOpenModal && modalOpen && (
        <BriefDetailModal digest={digest} onClose={() => setModalOpen(false)} />
      )}
    </>
  )
}
