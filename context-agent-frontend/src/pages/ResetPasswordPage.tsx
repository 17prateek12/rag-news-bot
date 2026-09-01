import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { AlertCircle, CheckCircle2, KeyRound } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()
  const { openAuth } = useAuth()

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!token) {
      setError('Password reset token is missing.')
      return
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)
    try {
      await api.resetPassword(token, newPassword)
      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!token) {
    return (
      <div className="page" style={{ maxWidth: '500px', margin: '40px auto', padding: '0 1rem' }}>
        <div className="modal-card" style={{ textAlign: 'center', padding: '2.5rem' }}>
          <AlertCircle size={48} className="text-danger" style={{ margin: '0 auto 1rem' }} />
          <h2>Invalid Reset Link</h2>
          <p className="muted" style={{ marginBottom: '1.5rem' }}>
            The password reset link is missing a valid token. Please request a new password reset link.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                navigate('/')
                openAuth('forgot-password')
              }}
            >
              Request New Reset Link
            </button>
            <Link to="/" className="btn btn-ghost">
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (success) {
    return (
      <div className="page" style={{ maxWidth: '500px', margin: '40px auto', padding: '0 1rem' }}>
        <div className="modal-card" style={{ textAlign: 'center', padding: '2.5rem' }}>
          <CheckCircle2 size={48} className="text-success" style={{ margin: '0 auto 1rem' }} />
          <h2>Password Reset Successful</h2>
          <p className="muted" style={{ marginBottom: '1.5rem' }}>
            Your password has been updated successfully. You can now log in with your new credentials.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-full"
            onClick={() => {
              navigate('/')
              openAuth('login')
            }}
          >
            Log In Now
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page" style={{ maxWidth: '500px', margin: '40px auto', padding: '0 1rem' }}>
      <div className="modal-card" style={{ padding: '2.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <KeyRound size={24} className="text-accent" />
          <h2 style={{ margin: 0 }}>Choose a New Password</h2>
        </div>
        <p className="muted" style={{ marginBottom: '1.5rem' }}>
          Create a secure password with at least 8 characters.
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            New Password
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => {
                  setNewPassword(e.target.value)
                  if (error) setError('')
                }}
                placeholder="At least 8 characters"
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>
          </label>

          <label>
            Confirm New Password
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value)
                if (error) setError('')
              }}
              placeholder="Re-enter your new password"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <button
            type="submit"
            className="btn btn-primary btn-full"
            disabled={submitting || !newPassword || !confirmPassword}
            style={{ marginTop: '0.5rem' }}
          >
            {submitting ? 'Updating Password…' : 'Set New Password'}
          </button>
        </form>
      </div>
    </div>
  )
}
