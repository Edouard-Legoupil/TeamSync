import { useEffect, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { TopBar } from './components/layout/TopBar'
import { ProgressProvider } from './components/ui/Progress'
import { Spinner } from './components/ui/Spinner'
import { ToastProvider } from './components/ui/Toast'
import AdminPage from './pages/AdminPage'
import AllMeetings from './pages/AllMeetings'
import Dashboard from './pages/Dashboard'
import MeetingDetail from './pages/MeetingDetail'
import MyItems from './pages/MyItems'
import Onboarding from './pages/Onboarding'
import SearchResults from './pages/SearchResults'
import TeamsPage from './pages/TeamsPage'

function FullScreenLoading() {
  return (
    <div className="flex h-screen items-center justify-center">
      <Spinner className="h-8 w-8" />
    </div>
  )
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, teams, loading, login } = useAuth()

  useEffect(() => {
    if (!loading && !user) login()
  }, [loading, user, login])

  if (loading || !user) return <FullScreenLoading />

  // First-login onboarding: a user with no team yet must pick one.
  if (teams.length === 0 && user.role !== 'SUPER_ADMIN') {
    return <Onboarding />
  }

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="flex-1">{children}</main>
    </div>
  )
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (user?.role !== 'SUPER_ADMIN') {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <h1 className="text-xl font-semibold text-navy-900">Access denied</h1>
        <p className="text-sm text-muted">You need administrator rights.</p>
      </div>
    )
  }
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <ProgressProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/team" replace />} />
            <Route
              path="/team"
              element={
                <RequireAuth>
                  <Dashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/meetings"
              element={
                <RequireAuth>
                  <AllMeetings />
                </RequireAuth>
              }
            />
            <Route
              path="/meetings/:id"
              element={
                <RequireAuth>
                  <MeetingDetail />
                </RequireAuth>
              }
            />
            <Route
              path="/my-items"
              element={
                <RequireAuth>
                  <MyItems />
                </RequireAuth>
              }
            />
            <Route
              path="/teams"
              element={
                <RequireAuth>
                  <TeamsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/search"
              element={
                <RequireAuth>
                  <SearchResults />
                </RequireAuth>
              }
            />
            <Route
              path="/admin"
              element={
                <RequireAuth>
                  <AdminOnly>
                    <AdminPage />
                  </AdminOnly>
                </RequireAuth>
              }
            />
            <Route path="*" element={<Navigate to="/team" replace />} />
          </Routes>
        </ProgressProvider>
      </ToastProvider>
    </AuthProvider>
  )
}
