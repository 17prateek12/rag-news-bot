import { type FormEvent, useEffect, memo, useCallback, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Loader2, Mic, Plus, Send, Square, Trash2 } from 'lucide-react'
import { api } from '../api/client'
import type { ChatMessage, ChatSession, SourceCitation } from '../api/types'
import { useAuth } from '../context/AuthContext'
import {
  VOICE_MESSAGE_LIMIT,
  canUseVoice,
  consumeVoice,
  getVoiceRemaining,
} from '../lib/voiceQuota'

function renderInlineStyles(text: string) {
  const parts = text.split(/(\*\*.*?\*\*|\[\d+(?:,\s*\d+)*\])/g)
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('[') && part.endsWith(']')) {
      return (
        <span key={idx} className="citation-badge">
          {part}
        </span>
      )
    }
    return part
  })
}

const MarkdownRenderer = memo(function MarkdownRenderer({ text }: { text: string }) {
  if (!text) return null
  const lines = text.split('\n')
  return (
    <div className="markdown-content">
      {lines.map((line, idx) => {
        const trimmed = line.trim()
        if (!trimmed) return null
        if (trimmed.startsWith('## ')) {
          const headerText = trimmed.replace(/^##\s+/, '')
          return (
            <h3 key={idx} className="markdown-h3">
              {renderInlineStyles(headerText)}
            </h3>
          )
        }
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          const itemText = trimmed.replace(/^[-*]\s+/, '')
          return (
            <ul key={idx} className="markdown-ul">
              <li className="markdown-li">
                {renderInlineStyles(itemText)}
              </li>
            </ul>
          )
        }
        return (
          <p key={idx} className="markdown-p">
            {renderInlineStyles(line)}
          </p>
        )
      })}
    </div>
  )
})

const SourcesList = memo(function SourcesList({ sources }: { sources: SourceCitation[] }) {
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

export function ChatPage() {
  const { user, loading: authLoading, openAuth } = useAuth()
  const navigate = useNavigate()
  const { sessionId } = useParams()
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState('')
  const [voiceRemaining, setVoiceRemaining] = useState(VOICE_MESSAGE_LIMIT)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const initializingRef = useRef(false)

  useEffect(() => {
    if (user) setVoiceRemaining(getVoiceRemaining(user.id))
  }, [user])

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('last_chat_session_id', sessionId)
    }
  }, [sessionId])

  useEffect(() => {
    if (!user) return
    let active = true
    ;(async () => {
      setLoadingSessions(true)
      try {
        const data = await api.listChatSessions()
        if (!active) return
        setSessions(data)
        if (!sessionId && !initializingRef.current) {
          initializingRef.current = true
          const lastId = localStorage.getItem('last_chat_session_id')
          const lastExists = lastId && data.some((s) => s.id === lastId)
          if (lastExists) {
            navigate(`/chat/${lastId}`, { replace: true })
            initializingRef.current = false
          } else if (data[0]) {
            navigate(`/chat/${data[0].id}`, { replace: true })
            initializingRef.current = false
          } else {
            try {
              const created = await api.createChatSession()
              if (active) {
                setSessions([created])
                navigate(`/chat/${created.id}`, { replace: true })
              }
            } finally {
              initializingRef.current = false
            }
          }
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Failed to load sessions')
        }
      } finally {
        if (active) {
          setLoadingSessions(false)
        }
      }
    })()
    return () => {
      active = false
    }
  }, [user, sessionId, navigate])

  useEffect(() => {
    if (!user || !sessionId) return
    ;(async () => {
      setLoadingMessages(true)
      setError('')
      try {
        const data = await api.listChatMessages(sessionId)
        setMessages(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load messages')
      } finally {
        setLoadingMessages(false)
      }
    })()
  }, [user, sessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const createSession = useCallback(async () => {
    const created = await api.createChatSession()
    setSessions((prev) => [created, ...prev])
    navigate(`/chat/${created.id}`)
  }, [navigate])

  const deleteSession = useCallback(async (id: string) => {
    await api.deleteChatSession(id)
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== id)
      if (sessionId === id) {
        if (remaining[0]) {
          navigate(`/chat/${remaining[0].id}`)
        } else {
          api.createChatSession().then((created) => {
            setSessions([created])
            navigate(`/chat/${created.id}`)
          })
        }
      }
      return remaining
    })
  }, [sessionId, navigate])

  const sendText = async (e?: FormEvent) => {
    e?.preventDefault()
    if (!sessionId || !input.trim() || sending) return
    const text = input.trim()
    setInput('')
    setSending(true)
    setError('')
    const tempUserMsg: ChatMessage = {
      id: 'temp-' + Date.now(),
      role: 'user',
      text: text,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    try {
      const res = await api.sendChatMessage(sessionId, text)
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        res.user_message,
        res.assistant_message,
      ])
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title: text.slice(0, 80) || s.title } : s)),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id))
      setInput(text)
    } finally {
      setSending(false)
    }
  }

  const sendAudio = async (blob: Blob) => {
    if (!sessionId || !user) return
    if (!canUseVoice(user.id)) {
      setError(`Voice limit reached (${VOICE_MESSAGE_LIMIT} messages per day).`)
      return
    }
    setSending(true)
    setError('')
    const tempUserMsg: ChatMessage = {
      id: 'temp-' + Date.now(),
      role: 'user',
      text: '🎤 Voice message...',
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    try {
      const res = await api.sendVoiceMessage(sessionId, blob, 'recording.webm')
      consumeVoice(user.id)
      setVoiceRemaining(getVoiceRemaining(user.id))
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        res.user_message,
        res.assistant_message,
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Voice message failed')
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id))
    } finally {
      setSending(false)
    }
  }

  const startRecording = async () => {
    if (!user || !canUseVoice(user.id)) {
      setError(`Voice limit reached (${VOICE_MESSAGE_LIMIT}/day).`)
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        await sendAudio(blob)
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      setError('Microphone access denied or unavailable.')
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  if (authLoading || !user) {
    return (
      <div className="page chat-page">
        <div className="empty-state">
          {authLoading ? 'Loading…' : (
            <>
              Please <button type="button" className="link-btn" onClick={() => openAuth('login')}>log in</button> to use chat.
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="page chat-page">
      <aside className="chat-sessions">
        <div className="chat-sessions-header">
          <h2>Chats</h2>
          <button type="button" className="icon-btn" onClick={createSession} aria-label="New chat">
            <Plus size={18} />
          </button>
        </div>
        {loadingSessions && <div className="empty-state small">Loading…</div>}
        <div className="chat-session-list">
          {sessions.map((session) => (
            <div key={session.id} className={`chat-session-item${sessionId === session.id ? ' active' : ''}`}>
              <Link to={`/chat/${session.id}`} className="chat-session-link">
                {session.title}
              </Link>
              <button
                type="button"
                className="icon-btn danger"
                onClick={() => void deleteSession(session.id)}
                aria-label="Delete chat"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="chat-main">
        <div className="chat-messages">
          {loadingMessages && <div className="empty-state">Loading messages…</div>}
          {!loadingMessages && !messages.length && (
            <div className="chat-empty">
              <h3>Ask about the news</h3>
              <p className="muted">
                Try “What is happening in Ukraine?” or follow up with “What about the economic impact?”
              </p>
            </div>
          )}
          {messages.map((message) => (
            <div key={message.id} className={`chat-bubble ${message.role}`}>
              <div className="chat-bubble-label">{message.role === 'user' ? 'You' : 'Agent'}</div>
              <div className="chat-bubble-text">
                <MarkdownRenderer text={message.text} />
              </div>
              {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                <SourcesList sources={message.sources} />
              )}
            </div>
          ))}
          {sending && (
            <div className="chat-bubble assistant pending">
              <Loader2 className="spin" size={18} /> Thinking…
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && <p className="error-text chat-error">{error}</p>}

        <form className="chat-input-bar" onSubmit={sendText}>
          <button
            type="button"
            className={`icon-btn mic-btn${recording ? ' recording' : ''}`}
            onClick={recording ? stopRecording : startRecording}
            disabled={sending || voiceRemaining <= 0}
            title={`Voice messages remaining today: ${voiceRemaining}/${VOICE_MESSAGE_LIMIT}`}
            aria-label={recording ? 'Stop recording' : 'Record voice message'}
          >
            {recording ? <Square size={18} /> : <Mic size={18} />}
          </button>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask for context, background, or latest updates…"
            disabled={sending || recording}
          />
          <button type="submit" className="btn btn-primary" disabled={sending || recording || !input.trim()}>
            <Send size={18} />
          </button>
        </form>
        <p className="chat-voice-quota muted">Voice: {voiceRemaining}/{VOICE_MESSAGE_LIMIT} left today</p>
      </section>
    </div>
  )
}
