import { type FormEvent, useEffect, useRef } from 'react'
import { Loader2, Mic, Send, Square } from 'lucide-react'
import type { ChatMessage } from '../../api/types'
import { MarkdownRenderer } from './MarkdownRenderer'
import { SourcesList } from './SourcesList'

interface ChatAreaProps {
  messages: ChatMessage[]
  loading: boolean
  sending: boolean
  error: string
  input: string
  recording: boolean
  voiceRemaining: number
  voiceLimit: number
  onInputChange: (value: string) => void
  onSendText: (e?: FormEvent) => void
  onStartRecording: () => void
  onStopRecording: () => void
}

export function ChatArea({
  messages,
  loading,
  sending,
  error,
  input,
  recording,
  voiceRemaining,
  voiceLimit,
  onInputChange,
  onSendText,
  onStartRecording,
  onStopRecording,
}: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  return (
    <section className="chat-main">
      <div className="chat-messages-container">
        <div className="chat-messages-inner">
          {loading && <div className="empty-state">Loading conversation…</div>}
          {!loading && messages.length === 0 && (
            <div className="chat-empty">
              <h3>Ask About the News</h3>
              <p className="muted">
                Ask questions about recent events, track stories, or request background context across all stored articles.
              </p>
            </div>
          )}
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-bubble ${msg.role}`}>
              <div className="chat-bubble-label">{msg.role === 'user' ? 'You' : 'Context Agent'}</div>
              <div className="chat-bubble-text">
                <MarkdownRenderer text={msg.text} />
              </div>
              {msg.sources && msg.sources.length > 0 && <SourcesList sources={msg.sources} />}
            </div>
          ))}
          {sending && (
            <div className="chat-bubble assistant pending">
              <div className="chat-bubble-label">Context Agent</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--muted)' }}>
                <Loader2 size={16} className="spin" />
                <span>Thinking & synthesizing answer…</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {error && <div className="form-error chat-error">{error}</div>}

      <div className="chat-input-container">
        <form className="chat-input-bar" onSubmit={onSendText}>
          <button
            type="button"
            className={`icon-btn mic-btn${recording ? ' recording' : ''}`}
            onClick={recording ? onStopRecording : onStartRecording}
            disabled={sending || voiceRemaining <= 0}
            title={`Voice messages remaining today: ${voiceRemaining}/${voiceLimit}`}
            aria-label={recording ? 'Stop recording' : 'Record voice message'}
          >
            {recording ? <Square size={18} /> : <Mic size={18} />}
          </button>
          <input
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            placeholder="Ask for context, background, or latest updates…"
            disabled={sending || recording}
          />
          <button type="submit" className="btn btn-primary" disabled={sending || recording || !input.trim()}>
            <Send size={18} />
          </button>
        </form>
        <p className="chat-voice-quota muted">Voice: {voiceRemaining}/{voiceLimit} left today</p>
      </div>
    </section>
  )
}
