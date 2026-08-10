import { type FormEvent, useState } from 'react'
import { X } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

export function AuthModal() {
  const { authOpen, authMode, closeAuth, login, register, openAuth } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!authOpen) return null

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      if (authMode === 'login') await login(email, password)
      else await register(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={closeAuth}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="icon-btn modal-close" onClick={closeAuth} aria-label="Close">
          <X size={20} />
        </button>
        <h2>{authMode === 'login' ? 'Welcome back' : 'Create account'}</h2>
        <p className="muted">
          {authMode === 'login'
            ? 'Sign in to chat with the news context agent.'
            : 'Register to save chat sessions and use voice input.'}
        </p>
        <form onSubmit={onSubmit} className="auth-form">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
            />
          </label>
          {error && <p className="error-text">{error}</p>}
          <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
            {submitting ? 'Please wait…' : authMode === 'login' ? 'Log in' : 'Sign up'}
          </button>
        </form>
        <p className="auth-switch muted">
          {authMode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            className="link-btn"
            onClick={() => openAuth(authMode === 'login' ? 'signup' : 'login')}
          >
            {authMode === 'login' ? 'Sign up' : 'Log in'}
          </button>
        </p>
      </div>
    </div>
  )
}
