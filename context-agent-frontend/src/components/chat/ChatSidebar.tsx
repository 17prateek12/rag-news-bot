import { Link } from 'react-router-dom'
import { Plus, Trash2 } from 'lucide-react'
import type { ChatSession } from '../../api/types'

interface ChatSidebarProps {
  sessions: ChatSession[]
  activeSessionId?: string
  loading: boolean
  onCreateSession: () => void
  onDeleteSession: (id: string) => void
}

export function ChatSidebar({
  sessions,
  activeSessionId,
  loading,
  onCreateSession,
  onDeleteSession,
}: ChatSidebarProps) {
  return (
    <aside className="chat-sessions">
      <div className="chat-sessions-header">
        <h2>Chats</h2>
        <button type="button" className="icon-btn" onClick={onCreateSession} aria-label="New chat">
          <Plus size={18} />
        </button>
      </div>
      {loading && <div className="empty-state small">Loading…</div>}
      <div className="chat-session-list">
        {sessions.map((session) => (
          <div key={session.id} className={`chat-session-item${activeSessionId === session.id ? ' active' : ''}`}>
            <Link to={`/chat/${session.id}`} className="chat-session-link">
              {session.title}
            </Link>
            <button
              type="button"
              className="icon-btn danger"
              onClick={() => onDeleteSession(session.id)}
              aria-label="Delete chat"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </aside>
  )
}
