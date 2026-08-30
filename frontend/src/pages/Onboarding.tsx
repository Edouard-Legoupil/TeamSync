import { useEffect, useState } from 'react'
import { Users } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { TeamInfo } from '../api/types'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { useToast } from '../components/ui/Toast'

export default function Onboarding() {
  const { user, refresh } = useAuth()
  const { toast } = useToast()
  const [teams, setTeams] = useState<TeamInfo[]>([])
  const [selected, setSelected] = useState('')
  const [joining, setJoining] = useState(false)

  useEffect(() => {
    api
      .get<TeamInfo[]>('/teams/available')
      .then(({ data }) => setTeams(data))
      .catch(() => setTeams([]))
  }, [])

  async function join() {
    if (!selected) return
    setJoining(true)
    try {
      await api.post(`/teams/${selected}/join`)
      await refresh()
      toast('Welcome to TeamSync!', 'success')
    } catch {
      toast('Could not join that team', 'error')
    } finally {
      setJoining(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <Card className="w-full max-w-md">
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-primary-50">
          <Users className="h-5 w-5 text-primary-600" />
        </div>
        <h1 className="text-xl font-semibold text-navy-900">
          Welcome, {user?.full_name || user?.email}
        </h1>
        <p className="mt-1 text-sm text-muted">
          Select the team you belong to, then you're in.
        </p>

        {teams.length ? (
          <div className="mt-4 space-y-3">
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
            >
              <option value="">Choose a team…</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <Button className="w-full" onClick={join} disabled={!selected || joining}>
              {joining ? 'Joining…' : 'Join team'}
            </Button>
          </div>
        ) : (
          <p className="mt-4 rounded-md border border-line bg-canvas/50 px-3 py-2 text-sm text-muted">
            No teams are available yet. Ask an administrator to create one and add you.
          </p>
        )}
      </Card>
    </div>
  )
}
