import { useQuery } from '@tanstack/react-query'
import { Bell, ExternalLink, Newspaper, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { useAuth } from '../../context/AuthContext'

export function DigestPanel() {
  const { user } = useAuth()

  const { data: digests = [], isLoading } = useQuery({
    queryKey: ['digests'],
    queryFn: () => api.listDigests(7),
    enabled: !!user,
  })

  if (!user || isLoading || digests.length === 0) {
    return null
  }

  // Render formatted summary with bullet points
  const renderSummary = (text: string) => {
    const lines = text.split('\n').filter((l) => l.trim().length > 0)
    return lines.map((line, idx) => {
      if (line.startsWith('- ') || line.startsWith('* ')) {
        return (
          <li key={idx} className="digest-bullet">
            {line.substring(2)}
          </li>
        )
      }
      if (line.toLowerCase().startsWith('key updates:')) {
        return (
          <h4 key={idx} className="digest-updates-title">
            Key Updates
          </h4>
        )
      }
      return (
        <p key={idx} className="digest-paragraph">
          {line}
        </p>
      )
    })
  }

  return (
    <section className="digest-panel">
      <div className="digest-panel-header">
        <div className="digest-panel-title">
          <Sparkles size={20} className="text-accent" />
          <h2>Today's Topic Briefs</h2>
        </div>
        <Link to="/watches" className="btn btn-ghost digest-manage-link">
          <Bell size={16} /> Manage Watches
        </Link>
      </div>

      <div className="digest-grid">
        {digests.map((d) => (
          <article key={d.id} className="digest-card">
            <div className="digest-card-header">
              <span className="badge badge-accent digest-keyword-badge">
                {d.keyword}
              </span>
              <span className="digest-date muted">{d.digest_date}</span>
            </div>

            <div className="digest-summary-content">
              {renderSummary(d.summary_text)}
            </div>

            {d.articles && d.articles.length > 0 && (
              <div className="digest-sources">
                <span className="digest-sources-label">
                  <Newspaper size={14} /> Sources ({d.articles.length}):
                </span>
                <div className="digest-source-chips">
                  {d.articles.map((art) => (
                    <a
                      key={art.id}
                      href={art.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="digest-source-chip"
                      title={art.title}
                    >
                      <span className="digest-source-title">{art.title}</span>
                      {art.source && (
                        <span className="digest-source-name">({art.source})</span>
                      )}
                      <ExternalLink size={12} />
                    </a>
                  ))}
                </div>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
