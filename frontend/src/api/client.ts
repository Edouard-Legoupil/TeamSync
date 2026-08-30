import axios from 'axios'

// The app JWT is delivered as an httpOnly cookie by /api/auth/callback, so the
// browser sends it automatically (withCredentials). This module additionally
// keeps an in-memory token for clients that prefer the Authorization header
// (e.g. dev-login programmatic access).
let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    if (status === 401 && typeof window !== 'undefined') {
      const { pathname } = window.location
      if (!pathname.startsWith('/api/auth/login')) {
        window.location.href = '/api/auth/login'
      }
    }
    return Promise.reject(error)
  },
)
