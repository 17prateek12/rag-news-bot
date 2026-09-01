import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../api/client'
import type { User } from '../api/types'

export type AuthMode =
  | 'login'
  | 'signup'
  | 'forgot-password'
  | 'reset-password'
  | 'change-password'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  changePassword: (current_password: string, new_password: string) => Promise<string>
  forgotPassword: (email: string) => Promise<string>
  resetPassword: (token: string, new_password: string) => Promise<string>
  logout: () => Promise<void>
  openAuth: (mode?: AuthMode) => void
  closeAuth: () => void
  authOpen: boolean
  authMode: AuthMode
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<AuthMode>('login')

  // H-2: No localStorage check — just always call /auth/me.
  // The httpOnly cookie is sent automatically by the browser; if the server
  // returns 401, the user is not logged in. This is the authoritative check.
  const refreshUser = useCallback(async () => {
    try {
      const me = await api.me()
      setUser(me)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshUser()
  }, [refreshUser])

  // H-2: login now receives the User directly from the server response;
  // the JWT is set as an httpOnly cookie by the server, never exposed to JS.
  const login = async (email: string, password: string) => {
    const me = await api.login(email, password)
    setUser(me)
    setAuthOpen(false)
  }

  const register = async (email: string, password: string) => {
    const me = await api.register(email, password)
    setUser(me)
    setAuthOpen(false)
  }

  const changePassword = async (current_password: string, new_password: string) => {
    const res = await api.changePassword(current_password, new_password)
    return res.message
  }

  const forgotPassword = async (email: string) => {
    const res = await api.forgotPassword(email)
    return res.message
  }

  const resetPassword = async (token: string, new_password: string) => {
    const res = await api.resetPassword(token, new_password)
    return res.message
  }

  // H-2: logout calls the server to clear the httpOnly cookie
  const logout = async () => {
    try {
      await api.logout()
    } catch {
      // Even if the server call fails, clear local state
    }
    setUser(null)
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      register,
      changePassword,
      forgotPassword,
      resetPassword,
      logout,
      openAuth: (mode: AuthMode = 'login') => {
        setAuthMode(mode)
        setAuthOpen(true)
      },
      closeAuth: () => setAuthOpen(false),
      authOpen,
      authMode,
    }),
    [user, loading, authOpen, authMode],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
