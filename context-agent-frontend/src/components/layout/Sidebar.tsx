import { NavLink } from 'react-router-dom'
import {
  Flame,
  Home,
  LogIn,
  LogOut,
  MessageSquare,
  Moon,
  Sun,
  UserPlus,
  X,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useTheme } from '../../context/ThemeContext'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout, openAuth } = useAuth()
  const { theme, toggleTheme } = useTheme()

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `sidebar-link${isActive ? ' active' : ''}`

  return (
    <>
      {open && <div className="sidebar-overlay open" onClick={onClose} aria-hidden="true" />}
      <aside className={`sidebar${open ? ' open' : ''}`} aria-hidden={!open}>
        <div className="sidebar-header">
          <span className="sidebar-title">Menu</span>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close menu">
            <X size={20} />
          </button>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" className={navClass} onClick={onClose}>
            <Home size={18} /> Home
          </NavLink>
          <NavLink to="/trending" className={navClass} onClick={onClose}>
            <Flame size={18} /> Trending
          </NavLink>
          <NavLink to="/chat" className={navClass} onClick={onClose}>
            <MessageSquare size={18} /> Chat
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <button type="button" className="sidebar-link" onClick={toggleTheme}>
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            {theme === 'light' ? 'Dark mode' : 'Light mode'}
          </button>
          {user ? (
            <>
              <div className="sidebar-user">{user.email}</div>
              <button type="button" className="sidebar-link" onClick={logout}>
                <LogOut size={18} /> Log out
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="sidebar-link"
                onClick={() => {
                  openAuth('login')
                  onClose()
                }}
              >
                <LogIn size={18} /> Log in
              </button>
              <button
                type="button"
                className="sidebar-link"
                onClick={() => {
                  openAuth('signup')
                  onClose()
                }}
              >
                <UserPlus size={18} /> Sign up
              </button>
            </>
          )}
        </div>
      </aside>
    </>
  )
}
