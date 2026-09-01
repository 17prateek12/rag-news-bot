import { type FormEvent, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import {
  VOICE_MESSAGE_LIMIT,
  canUseVoice,
  consumeVoice,
  getVoiceRemaining,
} from '../lib/voiceQuota'
import { ChatSidebar } from '../components/chat/ChatSidebar'
import { ChatArea } from '../components/chat/ChatArea'
import type { ChatMessage } from '../api/types'

export function ChatPage() {
  const { user, loading: authLoading, openAuth } = useAuth()
  const navigate = useNavigate()
  const { sessionId } = useParams()
  const queryClient = useQueryClient()

  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const [recording, setRecording] = useState(false)
  const [voiceRemaining, setVoiceRemaining] = useState(VOICE_MESSAGE_LIMIT)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  useEffect(() => {
    if (user) setVoiceRemaining(getVoiceRemaining(user.id))
  }, [user])

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('last_chat_session_id', sessionId)
    }
  }, [sessionId])

  // Fetch sessions using React Query (cached)
  const { data: sessions = [], isLoading: loadingSessions } = useQuery({
    queryKey: ['chatSessions'],
    queryFn: () => api.listChatSessions(),
    enabled: !!user,
  })

  // Fetch messages for active session (cached, refreshes on sessionId change)
  const { data: messages = [], isLoading: loadingMessages } = useQuery({
    queryKey: ['chatMessages', sessionId],
    queryFn: () => api.listChatMessages(sessionId!),
    enabled: !!user && !!sessionId,
  })

  // Mutation to create a new session
  const createSessionMutation = useMutation({
    mutationFn: (title?: string) => api.createChatSession(title),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] })
      navigate(`/chat/${created.id}`)
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to create chat session')
    },
  })

  // Mutation to delete a session
  const deleteSessionMutation = useMutation({
    mutationFn: (id: string) => api.deleteChatSession(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] })
      if (sessionId === deletedId) {
        const remaining = sessions.filter((s) => s.id !== deletedId)
        if (remaining[0]) {
          navigate(`/chat/${remaining[0].id}`)
        } else {
          createSessionMutation.mutate(undefined)
        }
      }
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : 'Failed to delete session')
    },
  })

  // Mutation to send a text message
  const sendMessageMutation = useMutation({
    mutationFn: (text: string) => api.sendChatMessage(sessionId!, text),
    onMutate: async (text) => {
      setError('')
      await queryClient.cancelQueries({ queryKey: ['chatMessages', sessionId] })
      const previousMessages = queryClient.getQueryData<ChatMessage[]>(['chatMessages', sessionId]) || []

      const tempUserMsg: ChatMessage = {
        id: 'temp-' + Date.now(),
        role: 'user',
        text: text,
        created_at: new Date().toISOString(),
      }

      queryClient.setQueryData<ChatMessage[]>(
        ['chatMessages', sessionId],
        [...previousMessages, tempUserMsg]
      )

      return { previousMessages }
    },
    onError: (err, _text, context) => {
      setError(err instanceof Error ? err.message : 'Failed to send message')
      if (context) {
        queryClient.setQueryData(['chatMessages', sessionId], context.previousMessages)
      }
    },
    onSuccess: (res, _text, context) => {
      if (context) {
        queryClient.setQueryData<ChatMessage[]>(
          ['chatMessages', sessionId],
          [...context.previousMessages, res.user_message, res.assistant_message]
        )
      }
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] })
    },
  })

  // Mutation to send a voice message
  const sendVoiceMutation = useMutation({
    mutationFn: (blob: Blob) => api.sendVoiceMessage(sessionId!, blob, 'recording.webm'),
    onMutate: async () => {
      setError('')
      await queryClient.cancelQueries({ queryKey: ['chatMessages', sessionId] })
      const previousMessages = queryClient.getQueryData<ChatMessage[]>(['chatMessages', sessionId]) || []

      const tempUserMsg: ChatMessage = {
        id: 'temp-' + Date.now(),
        role: 'user',
        text: '🎤 Voice message...',
        created_at: new Date().toISOString(),
      }

      queryClient.setQueryData<ChatMessage[]>(
        ['chatMessages', sessionId],
        [...previousMessages, tempUserMsg]
      )

      return { previousMessages }
    },
    onError: (err, _blob, context) => {
      setError(err instanceof Error ? err.message : 'Voice message failed')
      if (context) {
        queryClient.setQueryData(['chatMessages', sessionId], context.previousMessages)
      }
    },
    onSuccess: (res, _blob, context) => {
      if (context) {
        queryClient.setQueryData<ChatMessage[]>(
          ['chatMessages', sessionId],
          [...context.previousMessages, res.user_message, res.assistant_message]
        )
      }
      if (user) {
        consumeVoice(user.id)
        setVoiceRemaining(getVoiceRemaining(user.id))
      }
      queryClient.invalidateQueries({ queryKey: ['chatSessions'] })
    },
  })

  // Redirect to correct session if sessionId is missing
  useEffect(() => {
    if (!user || loadingSessions || !sessions) return
    if (!sessionId) {
      const lastId = localStorage.getItem('last_chat_session_id')
      const lastExists = lastId && sessions.some((s) => s.id === lastId)
      if (lastExists) {
        navigate(`/chat/${lastId}`, { replace: true })
      } else if (sessions[0]) {
        navigate(`/chat/${sessions[0].id}`, { replace: true })
      } else {
        createSessionMutation.mutate(undefined)
      }
    }
  }, [user, sessions, sessionId, loadingSessions, navigate])

  const handleSendText = (e?: FormEvent) => {
    e?.preventDefault()
    if (!sessionId || !input.trim() || sendMessageMutation.isPending) return
    const text = input.trim()
    setInput('')
    sendMessageMutation.mutate(text)
  }

  const handleStartRecording = async () => {
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
        sendVoiceMutation.mutate(blob)
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setRecording(true)
    } catch {
      setError('Microphone access denied or unavailable.')
    }
  }

  const handleStopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  if (authLoading || !user) {
    return (
      <div className="page chat-page">
        <div className="empty-state">
          {authLoading ? (
            'Loading…'
          ) : (
            <>
              Please{' '}
              <button
                type="button"
                className="link-btn"
                onClick={() => openAuth('login')}
              >
                log in
              </button>{' '}
              to use chat.
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="page chat-page">
      <ChatSidebar
        sessions={sessions}
        activeSessionId={sessionId}
        loading={loadingSessions}
        onCreateSession={() => createSessionMutation.mutate(undefined)}
        onDeleteSession={(id) => deleteSessionMutation.mutate(id)}
      />

      <ChatArea
        messages={messages}
        loading={loadingMessages}
        sending={sendMessageMutation.isPending || sendVoiceMutation.isPending}
        error={error}
        input={input}
        recording={recording}
        voiceRemaining={voiceRemaining}
        voiceLimit={VOICE_MESSAGE_LIMIT}
        onInputChange={setInput}
        onSendText={handleSendText}
        onStartRecording={handleStartRecording}
        onStopRecording={handleStopRecording}
      />
    </div>
  )
}