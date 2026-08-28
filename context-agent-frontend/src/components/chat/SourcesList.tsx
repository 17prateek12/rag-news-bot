import { memo } from 'react'
import type { SourceCitation } from '../../api/types'

interface SourcesListProps {
  sources: SourceCitation[]
}

export const SourcesList = memo(function SourcesList({ sources }: SourcesListProps) {
  if (!sources.length) return null
  return (
    <div className="chat-sources">
      <strong>Sources</strong>
      <ul>
        {sources.map((source) => (
          <li key={source.index}>
            <a href={source.url} target="_blank" rel="noreferrer">
              [{source.index}] {source.title} ({source.source})
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
})
