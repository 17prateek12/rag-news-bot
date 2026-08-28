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
      <div className="chat-messages">
        {loading && <div className="empty-state">Loading messages…</div>}
        {!loading && !messages.length && (
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
    </section>
  )
}
