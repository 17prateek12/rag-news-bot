import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'

const HomePage = lazy(() => import('./pages/HomePage').then(module => ({ default: module.HomePage })))
const TrendingPage = lazy(() => import('./pages/TrendingPage').then(module => ({ default: module.TrendingPage })))
const ChatPage = lazy(() => import('./pages/ChatPage').then(module => ({ default: module.ChatPage })))

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Suspense fallback={<div className="empty-state" style={{ padding: '40px', textAlign: 'center' }}>Loading...</div>}>
            <Routes>
              <Route element={<AppLayout />}>
                <Route index element={<HomePage />} />
                <Route path="trending" element={<TrendingPage />} />
                <Route path="chat" element={<ChatPage />} />
                <Route path="chat/:sessionId" element={<ChatPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
