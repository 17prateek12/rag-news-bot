import { type FormEvent, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Menu, Moon, Search, Sun } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useTheme } from '../../context/ThemeContext'

interface NavbarProps {
  onMenuClick: () => void
  onSearch: (query: string) => void
  searchQuery?: string
}

export function Navbar({ onMenuClick, onSearch, searchQuery = '' }: NavbarProps) {
  const { user, openAuth, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [query, setQuery] = useState(searchQuery)

  useEffect(() => {
    setQuery(searchQuery)
  }, [searchQuery])

  useEffect(() => {
    if (query.trim() === searchQuery.trim()) return

    const delay = setTimeout(() => {
      onSearch(query.trim())
    }, 400)

    return () => clearTimeout(delay)
  }, [query, searchQuery, onSearch])

  const submit = (e: FormEvent) => {
    e.preventDefault()
    onSearch(query.trim())
  }

  return (
    <header className="navbar">
      <div className="navbar-left">
        <button type="button" className="icon-btn" onClick={onMenuClick} aria-label="Open menu">
          <Menu size={22} />
        </button>
        <Link to="/" className="brand">
          <span className="brand-mark">CA</span>
          <span className="brand-text">Context Agent</span>
        </Link>
      </div>
      <form className="navbar-search" onSubmit={submit}>
        <Search size={18} className="search-icon" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search news, topics, or ask a question…"
          aria-label="Search"
        />
      </form>
      <div className="navbar-right">
        <button type="button" className="icon-btn theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
        </button>
        {user ? (
          <>
            <span className="navbar-user hide-mobile">{user.email}</span>
            <button type="button" className="btn btn-ghost" onClick={logout}>
              Log out
            </button>
          </>
        ) : (
          <>
            <button type="button" className="btn btn-ghost" onClick={() => openAuth('login')}>
              Log in
            </button>
            <button type="button" className="btn btn-primary" onClick={() => openAuth('signup')}>
              Sign up
            </button>
          </>
        )}
      </div>
    </header>
  )
}
