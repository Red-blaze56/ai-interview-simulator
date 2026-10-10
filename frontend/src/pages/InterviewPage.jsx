import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import AnswerInput from '../components/AnswerInput.jsx'
import MessageBubble from '../components/MessageBubble.jsx'
import Report from '../components/Report.jsx'

export default function InterviewPage() {
  const { id } = useParams()
  const [interview, setInterview] = useState(null)
  const [pending, setPending] = useState(null) // optimistic candidate message
  const [shouldFinish, setShouldFinish] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    setInterview(null)
    setShouldFinish(false)
    setError('')
    api.getInterview(id).then(setInterview).catch((e) => setError(e.message))
  }, [id])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [interview?.messages.length, pending, busy])

  async function send(content) {
    setError('')
    setBusy(true)
    setPending({ id: 'pending', sender: 'candidate', content })
    try {
      const res = await api.answer(id, content)
      setInterview(res.interview) // server is the source of truth for the transcript
      if (res.should_finish) setShouldFinish(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setPending(null)
      setBusy(false)
    }
  }

  async function finish() {
    setError('')
    setBusy(true)
    try {
      setInterview(await api.finish(id))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (!interview) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>

  const finished = interview.status === 'finished'
  const messages = pending ? [...interview.messages, pending] : interview.messages

  return (
    <div className="chat">
      <div className="chat-head">
        <h1>{interview.programming_language} · {interview.candidate_level}</h1>
        <span className={`badge ${interview.status}`}>{interview.status}</span>
        {!finished && (
          <button onClick={finish} disabled={busy} className={shouldFinish ? 'primary' : ''}>Finish &amp; get report</button>
        )}
      </div>

      <div className="thread">
        {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
        {busy && pending && <div className="muted typing">Interviewer is thinking…</div>}
        {busy && !pending && <div className="muted typing">Generating report…</div>}
        <div ref={endRef} />
      </div>

      {error && <p className="error">{error}</p>}
      {finished ? (
        <>
          {interview.report && <Report report={interview.report} />}
          <Link to="/new">Start another interview</Link>
        </>
      ) : (
        <>
          {shouldFinish && <p className="notice">The interviewer has wrapped up. Click “Finish &amp; get report”.</p>}
          <AnswerInput onSubmit={send} disabled={busy || shouldFinish} />
        </>
      )}
    </div>
  )
}
