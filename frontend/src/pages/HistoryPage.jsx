import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function HistoryPage() {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listInterviews().then(setItems).catch((e) => setError(e.message))
  }, [])

  if (error) return <p className="error">{error}</p>
  if (!items) return <p className="muted">Loading…</p>

  return (
    <>
      <h1>Your interviews</h1>
      {items.length === 0 && <p className="muted">No interviews yet. <Link to="/new">Start one</Link>.</p>}
      <div className="cards">
        {items.map((i) => (
          <Link key={i.id} to={`/interviews/${i.id}`} className="card item">
            <strong>{i.programming_language} · {i.candidate_level}</strong>
            <span className={`badge ${i.status}`}>{i.status}</span>
            <span className="muted">{new Date(i.created_at).toLocaleString()}</span>
          </Link>
        ))}
      </div>
    </>
  )
}
