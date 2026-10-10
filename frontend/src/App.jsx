import { Link, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import AuthPage from './pages/AuthPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import InterviewPage from './pages/InterviewPage.jsx'
import NewInterviewPage from './pages/NewInterviewPage.jsx'

function Layout() {
  const { user, logout } = useAuth()
  return (
    <>
      <header className="nav">
        <Link to="/" className="brand">AI Interview Simulator</Link>
        <nav>
          <Link to="/new">New interview</Link>
          <Link to="/">History</Link>
          <span className="muted">{user.email}</span>
          <button className="link" onClick={logout}>Log out</button>
        </nav>
      </header>
      <main><Outlet /></main>
    </>
  )
}

function RequireAuth() {
  const { user, loading } = useAuth()
  if (loading) return <p className="center muted">Loading…</p>
  return user ? <Layout /> : <Navigate to="/login" replace />
}

export default function App() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <AuthPage mode="login" />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <AuthPage mode="register" />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<HistoryPage />} />
        <Route path="/new" element={<NewInterviewPage />} />
        <Route path="/interviews/:id" element={<InterviewPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
