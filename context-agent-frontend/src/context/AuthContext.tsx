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

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  openAuth: (mode?: 'login' | 'signup') => void
  closeAuth: () => void
  authOpen: boolean
  authMode: 'login' | 'signup'
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [authOpen, setAuthOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login')

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
      logout,
      openAuth: (mode: 'login' | 'signup' = 'login') => {
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
