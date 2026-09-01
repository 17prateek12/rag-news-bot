import { type FormEvent, useState } from 'react'
import { createPortal } from 'react-dom'
import { CheckCircle2, KeyRound, X } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

export function AuthModal() {
  const {
    authOpen,
    authMode,
    closeAuth,
    login,
    register,
    changePassword,
    forgotPassword,
    resetPassword,
    openAuth,
  } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [resetToken, setResetToken] = useState('')

  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (!authOpen) return null

  const resetFormState = () => {
    setError('')
    setSuccessMessage('')
  }

  const handleLoginOrSignup = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMessage('')
    setSubmitting(true)
    try {
      if (authMode === 'login') {
        await login(email, password)
      } else {
        await register(email, password)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleForgotPassword = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMessage('')
    setSubmitting(true)
    try {
      const msg = await forgotPassword(email)
      setSuccessMessage(msg)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process request')
    } finally {
      setSubmitting(false)
    }
  }

  const handleResetPassword = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMessage('')
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match')
      return
    }
    setSubmitting(true)
    try {
      const msg = await resetPassword(resetToken, newPassword)
      setSuccessMessage(msg)
      setTimeout(() => {
        openAuth('login')
        resetFormState()
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password')
    } finally {
      setSubmitting(false)
    }
  }

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMessage('')
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match')
      return
    }
    setSubmitting(true)
    try {
      const msg = await changePassword(currentPassword, newPassword)
      setSuccessMessage(msg)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setTimeout(() => {
        closeAuth()
        resetFormState()
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to change password')
    } finally {
      setSubmitting(false)
    }
  }

  return createPortal(
    <div className="modal-backdrop" onClick={closeAuth}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          className="icon-btn modal-close"
          onClick={closeAuth}
          aria-label="Close"
        >
          <X size={20} />
        </button>

        {/* 1. Login / Signup View */}
        {(authMode === 'login' || authMode === 'signup') && (
          <>
            <h2>{authMode === 'login' ? 'Welcome back' : 'Create account'}</h2>
            <p className="muted">
              {authMode === 'login'
                ? 'Sign in to chat with the news context agent.'
                : 'Register to save chat sessions, manage topic watches, and use voice input.'}
            </p>
            <form onSubmit={handleLoginOrSignup} className="auth-form">
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
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Password</span>
                  {authMode === 'login' && (
                    <button
                      type="button"
                      className="link-btn"
                      style={{ fontSize: '0.8rem' }}
                      onClick={() => {
                        resetFormState()
                        openAuth('forgot-password')
                      }}
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
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
                onClick={() => {
                  resetFormState()
                  openAuth(authMode === 'login' ? 'signup' : 'login')
                }}
              >
                {authMode === 'login' ? 'Sign up' : 'Log in'}
              </button>
            </p>
          </>
        )}

        {/* 2. Forgot Password View */}
        {authMode === 'forgot-password' && (
          <>
            <h2>Forgot Password</h2>
            <p className="muted">
              Enter your registered email address to receive password reset instructions in your inbox.
            </p>
            <form onSubmit={handleForgotPassword} className="auth-form">
              <label>
                Registered Email
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </label>

              {error && <p className="error-text">{error}</p>}
              {successMessage && (
                <div className="auth-success-box">
                  <CheckCircle2 size={18} className="text-success" />
                  <p>{successMessage}</p>
                </div>
              )}

              {!successMessage && (
                <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                  {submitting ? 'Sending Link…' : 'Send Reset Link'}
                </button>
              )}
            </form>
            <p className="auth-switch muted">
              <button
                type="button"
                className="link-btn"
                onClick={() => {
                  resetFormState()
                  openAuth('login')
                }}
              >
                ← Back to Log in
              </button>
            </p>
          </>
        )}

        {/* 3. Reset Password View */}
        {authMode === 'reset-password' && (
          <>
            <h2>Set New Password</h2>
            <p className="muted">
              Enter the reset token along with your desired new password.
            </p>
            <form onSubmit={handleResetPassword} className="auth-form">
              <label>
                Reset Token
                <input
                  type="text"
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  placeholder="Paste your reset token here"
                  required
                />
              </label>
              <label>
                New Password (min 8 characters)
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </label>
              <label>
                Confirm New Password
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </label>

              {error && <p className="error-text">{error}</p>}
              {successMessage && (
                <div className="auth-success-box">
                  <CheckCircle2 size={18} className="text-success" />
                  <p>{successMessage}</p>
                </div>
              )}

              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Resetting Password…' : 'Set New Password'}
              </button>
            </form>
            <p className="auth-switch muted">
              <button
                type="button"
                className="link-btn"
                onClick={() => {
                  resetFormState()
                  openAuth('login')
                }}
              >
                ← Back to Log in
              </button>
            </p>
          </>
        )}

        {/* 4. Change Password View (Authenticated) */}
        {authMode === 'change-password' && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <KeyRound size={22} className="text-accent" />
              <h2>Change Password</h2>
            </div>
            <p className="muted">
              Enter your current password followed by your new password.
            </p>
            <form onSubmit={handleChangePassword} className="auth-form">
              <label>
                Current Password
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                />
              </label>
              <label>
                New Password (min 8 characters)
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </label>
              <label>
                Confirm New Password
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </label>

              {error && <p className="error-text">{error}</p>}
              {successMessage && (
                <div className="auth-success-box">
                  <CheckCircle2 size={18} className="text-success" />
                  <p>{successMessage}</p>
                </div>
              )}

              <button type="submit" className="btn btn-primary btn-full" disabled={submitting}>
                {submitting ? 'Updating…' : 'Update Password'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>,
    document.body
  )
}
