import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, getToken, setToken } from '../api/client'
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
  logout: () => void
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

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await api.me()
      setUser(me)
    } catch {
      setToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshUser()
  }, [refreshUser])

  const login = async (email: string, password: string) => {
    const res = await api.login(email, password)
    setToken(res.access_token)
    const me = await api.me()
    setUser(me)
    setAuthOpen(false)
  }

  const register = async (email: string, password: string) => {
    const res = await api.register(email, password)
    setToken(res.access_token)
    const me = await api.me()
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

  const logout = () => {
    setToken(null)
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
