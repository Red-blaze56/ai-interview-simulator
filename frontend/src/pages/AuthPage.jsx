import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth.jsx'

export default function AuthPage({ mode }) {
  const isRegister = mode === 'register'
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      if (isRegister) await api.register(email, password)
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="auth card">
      <h1>{isRegister ? 'Create account' : 'Log in'}</h1>
      <form onSubmit={onSubmit}>
        <label>Email
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
        </label>
        <label>Password
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? 'Please wait…' : isRegister ? 'Register' : 'Log in'}</button>
      </form>
      <p className="muted">
        {isRegister ? <>Have an account? <Link to="/login">Log in</Link></> : <>No account? <Link to="/register">Register</Link></>}
      </p>
    </div>
  )
}
