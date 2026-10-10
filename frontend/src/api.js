const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

// FastAPI errors: {detail: "msg"} or {detail: [{msg, loc}, ...]}
function errorMessage(body, fallback) {
  const d = body?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((e) => e.msg).join('; ')
  return fallback
}

async function request(path, { method = 'GET', json, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let body
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  } else if (form) {
    body = new URLSearchParams(form) // sets application/x-www-form-urlencoded
  }

  let res
  try {
    res = await fetch(BASE + path, { method, headers, body })
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Is the backend running?')
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    // Expired/invalid token on an authed call: drop it and let the app redirect.
    if (res.status === 401 && token) {
      clearToken()
      window.dispatchEvent(new Event('auth:logout'))
    }
    throw new ApiError(res.status, errorMessage(data, `Request failed (${res.status})`))
  }
  return data
}

export const api = {
  register: (email, password) => request('/auth/register', { method: 'POST', json: { email, password } }),
  login: (email, password) =>
    request('/auth/login', { method: 'POST', form: { username: email, password } }),
  me: () => request('/auth/me'),

  createInterview: (payload) => request('/interviews', { method: 'POST', json: payload }),
  listInterviews: () => request('/interviews'),
  getInterview: (id) => request(`/interviews/${id}`),
  answer: (id, content) => request(`/interviews/${id}/answer`, { method: 'POST', json: { content } }),
  finish: (id) => request(`/interviews/${id}/finish`, { method: 'POST' }),
}
