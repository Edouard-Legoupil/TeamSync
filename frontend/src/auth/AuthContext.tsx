import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../api/client'
import type { MeResponse, Team, User } from '../api/types'

const TEAM_STORAGE_KEY = 'teamsync:teamId'

export const ALL_TEAMS = '__all__'

interface AuthContextValue {
  user: User | null
  teams: Team[]
  currentTeamId: string | null
  loading: boolean
  login: () => void
  logout: () => Promise<void>
  setCurrentTeamId: (id: string) => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [teams, setTeams] = useState<Team[]>([])
  const [currentTeamId, setCurrentTeamId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get<MeResponse>('/auth/me')
      setUser(data.user)
      setTeams(data.teams)
      const stored = localStorage.getItem(TEAM_STORAGE_KEY)
      const valid =
        stored === ALL_TEAMS || (!!stored && data.teams.some((t) => t.id === stored))
      setCurrentTeamId(valid ? stored : data.primary_team_id)
    } catch {
      setUser(null)
      setTeams([])
      setCurrentTeamId(null)
    }
  }, [])

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [refresh])

  const login = useCallback(() => {
    window.location.href = '/api/auth/login'
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.get('/auth/logout')
    } catch {
      // Ignore — clear local state regardless.
    }
    localStorage.removeItem(TEAM_STORAGE_KEY)
    setUser(null)
    setTeams([])
    setCurrentTeamId(null)
    window.location.href = '/team'
  }, [])

  const handleSetTeam = useCallback((id: string) => {
    setCurrentTeamId(id)
    localStorage.setItem(TEAM_STORAGE_KEY, id)
  }, [])

  const value = useMemo(
    () => ({
      user,
      teams,
      currentTeamId,
      loading,
      login,
      logout,
      setCurrentTeamId: handleSetTeam,
      refresh,
    }),
    [user, teams, currentTeamId, loading, login, logout, handleSetTeam, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
