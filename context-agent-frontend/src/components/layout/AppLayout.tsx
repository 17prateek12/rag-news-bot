import { useState } from 'react'
import { Outlet, useNavigate, useSearchParams } from 'react-router-dom'
import { AuthModal } from '../auth/AuthModal'
import { Navbar } from './Navbar'
import { Sidebar } from './Sidebar'

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const onSearch = (query: string) => {
    if (!query) {
      setSearchParams({})
      return
    }
    setSearchParams({ q: query })
    if (window.location.pathname !== '/') navigate('/')
  }

  return (
    <div className="app-shell">
      <Navbar
        onMenuClick={() => setSidebarOpen(true)}
        onSearch={onSearch}
        searchQuery={searchParams.get('q') ?? ''}
      />
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main className="app-main">
        <Outlet />
      </main>
      <AuthModal />
    </div>
  )
}
