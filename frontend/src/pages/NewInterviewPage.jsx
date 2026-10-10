import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const OPTIONS = {
  programming_language: ['python', 'javascript', 'java', 'csharp', 'ruby', 'go', 'php', 'cplusplus', 'swift', 'kotlin'],
  candidate_level: ['intern', 'fresher', 'junior', 'mid', 'senior'],
  personality_type: ['strict', 'warm', 'engineering', 'academic', 'sarcasm', 'coaching'],
  correction_mode: ['strict', 'guided'],
}
const LABELS = {
  programming_language: 'Language',
  candidate_level: 'Level',
  personality_type: 'Interviewer personality',
  correction_mode: 'Correction mode',
}

export default function NewInterviewPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    programming_language: 'python',
    candidate_level: 'junior',
    personality_type: 'warm',
    correction_mode: 'guided',
    resume_text: '',
    jd_text: '',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    const payload = { ...form }
    if (!payload.resume_text.trim()) delete payload.resume_text
    if (!payload.jd_text.trim()) delete payload.jd_text
    try {
      const interview = await api.createInterview(payload)
      navigate(`/interviews/${interview.id}`)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="card narrow">
      <h1>New interview</h1>
      <form onSubmit={onSubmit}>
        <div className="grid2">
          {Object.entries(OPTIONS).map(([key, values]) => (
            <label key={key}>{LABELS[key]}
              <select value={form[key]} onChange={set(key)}>
                {values.map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </label>
          ))}
        </div>
        <label>Resume (optional)
          <textarea rows={5} value={form.resume_text} onChange={set('resume_text')} placeholder="Paste your resume text" />
        </label>
        <label>Job description (optional)
          <textarea rows={5} value={form.jd_text} onChange={set('jd_text')} placeholder="Paste the job description" />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? 'Starting… (the interviewer is preparing)' : 'Start interview'}</button>
      </form>
    </div>
  )
}
