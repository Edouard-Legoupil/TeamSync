import { useCallback, useEffect, useState } from 'react'
import { Building, Plus, Trash2, Users as UsersIcon } from 'lucide-react'
import { api } from '../api/client'
import type { AdminMember, AdminTeam, AdminUser } from '../api/types'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'

const ROLES = ['SUPER_ADMIN', 'SUPERVISOR', 'MEMBER']
const MEMBER_ROLES = ['LEAD', 'CONTRIBUTOR', 'VIEWER']

function descendantIds(teamId: string, teams: AdminTeam[]): Set<string> {
  const result = new Set<string>()
  let frontier = [teamId]
  while (frontier.length) {
    const next: string[] = []
    for (const t of teams) {
      if (t.parent_team_id && frontier.includes(t.parent_team_id) && !result.has(t.id)) {
        result.add(t.id)
        next.push(t.id)
      }
    }
    frontier = next
  }
  return result
}

type Tab = 'users' | 'teams'

export default function AdminPage() {
  const { toast } = useToast()
  const [tab, setTab] = useState<Tab>('users')
  const [users, setUsers] = useState<AdminUser[]>([])
  const [teams, setTeams] = useState<AdminTeam[]>([])
  const [loading, setLoading] = useState(true)

  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null)
  const [members, setMembers] = useState<AdminMember[]>([])
  const [newTeamName, setNewTeamName] = useState('')
  const [newTeamParentId, setNewTeamParentId] = useState('')
  const [rename, setRename] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editParentId, setEditParentId] = useState('')
  const [newMemberId, setNewMemberId] = useState('')
  const [newMemberRole, setNewMemberRole] = useState('VIEWER')

  const loadUsers = useCallback(async () => {
    const { data } = await api.get<AdminUser[]>('/admin/users')
    setUsers(data)
  }, [])

  const loadTeams = useCallback(async () => {
    const { data } = await api.get<AdminTeam[]>('/admin/teams')
    setTeams(data)
  }, [])

  const loadMembers = useCallback(async (teamId: string) => {
    const { data } = await api.get<AdminMember[]>(`/admin/teams/${teamId}/members`)
    setMembers(data)
  }, [])

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      await Promise.all([loadUsers(), loadTeams()])
    } catch {
      toast('Could not load admin data', 'error')
    } finally {
      setLoading(false)
    }
  }, [loadUsers, loadTeams, toast])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  async function updateUser(id: string, patch: { role?: string; is_active?: boolean }) {
    try {
      await api.patch(`/admin/users/${id}`, patch)
      await loadUsers()
    } catch {
      toast('Could not update user', 'error')
    }
  }

  async function createTeam() {
    const name = newTeamName.trim()
    if (!name) return
    try {
      await api.post('/admin/teams', {
        name,
        parent_team_id: newTeamParentId || null,
      })
      setNewTeamName('')
      setNewTeamParentId('')
      toast('Team created', 'success')
    } catch {
      toast('Could not create team', 'error')
      return
    }
    try {
      await loadTeams()
    } catch {
      toast('Team created, but the list could not be refreshed', 'error')
    }
  }

  async function saveTeam() {
    const name = rename.trim()
    if (!name || !selectedTeamId) return
    try {
      await api.patch(`/admin/teams/${selectedTeamId}`, {
        name,
        description: editDescription.trim() || null,
        parent_team_id: editParentId || null,
      })
      await loadTeams()
      toast('Team updated', 'success')
    } catch {
      toast('Could not update team', 'error')
    }
  }

  async function deleteTeam(id: string) {
    try {
      await api.delete(`/admin/teams/${id}`)
      setSelectedTeamId(null)
      setMembers([])
      await loadTeams()
    } catch {
      toast('Could not delete team', 'error')
    }
  }

  function selectTeam(team: AdminTeam) {
    setSelectedTeamId(team.id)
    setRename(team.name)
    setEditDescription(team.description ?? '')
    setEditParentId(team.parent_team_id ?? '')
    loadMembers(team.id)
  }

  async function addMember() {
    if (!selectedTeamId || !newMemberId) return
    try {
      await api.post(`/admin/teams/${selectedTeamId}/members`, {
        user_id: newMemberId,
        role: newMemberRole,
      })
      setNewMemberId('')
      await loadMembers(selectedTeamId)
      await loadTeams()
    } catch {
      toast('Could not add member', 'error')
    }
  }

  async function updateMember(userId: string, role: string) {
    if (!selectedTeamId) return
    try {
      await api.patch(`/admin/teams/${selectedTeamId}/members/${userId}`, { role })
      await loadMembers(selectedTeamId)
    } catch {
      toast('Could not update member', 'error')
    }
  }

  async function removeMember(userId: string) {
    if (!selectedTeamId) return
    try {
      await api.delete(`/admin/teams/${selectedTeamId}/members/${userId}`)
      await loadMembers(selectedTeamId)
      await loadTeams()
    } catch {
      toast('Could not remove member', 'error')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  const memberIds = new Set(members.map((m) => m.user_id))
  const addableUsers = users.filter((u) => !memberIds.has(u.id))
  const blockedParentIds = selectedTeamId
    ? descendantIds(selectedTeamId, teams)
    : new Set<string>()
  const parentOptions = teams.filter(
    (t) => t.id !== selectedTeamId && !blockedParentIds.has(t.id),
  )

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold text-navy-900">Administration</h1>
      <p className="text-sm text-muted">Manage users, teams, and team access.</p>

      <div className="mt-6 flex gap-1 border-b border-line">
        {(
          [
            ['users', 'Users'],
            ['teams', 'Teams'],
          ] as [Tab, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium ${
              tab === id
                ? 'border-primary-600 text-primary-700'
                : 'border-transparent text-muted hover:text-navy-900'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'users' ? (
        <Card className="mt-6 overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-line bg-canvas/50 text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-semibold">User</th>
                  <th className="px-4 py-3 font-semibold">Role</th>
                  <th className="px-4 py-3 font-semibold">Teams</th>
                  <th className="px-4 py-3 font-semibold">Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="px-4 py-3">
                      <p className="font-medium text-navy-900">{u.full_name || '—'}</p>
                      <p className="text-xs text-muted">{u.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={u.role}
                        onChange={(e) => updateUser(u.id, { role: e.target.value })}
                        className="rounded-md border border-line bg-white px-2 py-1.5 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-muted">{u.team_count}</td>
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={u.is_active}
                        onChange={(e) => updateUser(u.id, { is_active: e.target.checked })}
                        className="h-4 w-4 cursor-pointer rounded border-line accent-primary-600"
                        aria-label={`Toggle active for ${u.email}`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Teams list */}
          <div>
            <div className="flex gap-2">
              <input
                value={newTeamName}
                onChange={(e) => setNewTeamName(e.target.value)}
                placeholder="New team name…"
                className="min-w-0 flex-1 rounded-md border border-line px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
              />
              <Button onClick={createTeam}>
                <Plus className="h-4 w-4" />
                Create
              </Button>
            </div>
            <select
              value={newTeamParentId}
              onChange={(e) => setNewTeamParentId(e.target.value)}
              className="mt-2 w-full rounded-md border border-line px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
            >
              <option value="">No parent (top-level)</option>
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  Child of {t.name}
                </option>
              ))}
            </select>

            <ul className="mt-4 space-y-2">
              {teams.map((team) => (
                <li key={team.id}>
                  <div
                    className={`flex cursor-pointer items-center justify-between rounded-md border px-3 py-2.5 ${
                      selectedTeamId === team.id
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-line bg-white hover:bg-canvas/60'
                    }`}
                    onClick={() => selectTeam(team)}
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-navy-900">{team.name}</p>
                      <p className="text-xs text-muted">{team.member_count} members</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        deleteTeam(team.id)
                      }}
                      aria-label={`Delete ${team.name}`}
                      className="text-muted hover:text-danger"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Selected team members */}
          <div>
            {selectedTeamId ? (
              <Card>
                <div className="mb-4 space-y-3">
                  <div>
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                      Name
                    </label>
                    <input
                      value={rename}
                      onChange={(e) => setRename(e.target.value)}
                      className="w-full rounded-md border border-line px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                      Description
                    </label>
                    <input
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      className="w-full rounded-md border border-line px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                      Parent team
                    </label>
                    <select
                      value={editParentId}
                      onChange={(e) => setEditParentId(e.target.value)}
                      className="w-full rounded-md border border-line px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                    >
                      <option value="">No parent (top-level)</option>
                      {parentOptions.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button onClick={saveTeam} disabled={!rename.trim()}>
                    Save team
                  </Button>
                </div>

                <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-navy-900">
                  <UsersIcon className="h-4 w-4" />
                  Members
                </h3>

                <div className="flex gap-2">
                  <select
                    value={newMemberId}
                    onChange={(e) => setNewMemberId(e.target.value)}
                    className="min-w-0 flex-1 rounded-md border border-line px-2 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                  >
                    <option value="">Add user…</option>
                    {addableUsers.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name || u.email}
                      </option>
                    ))}
                  </select>
                  <select
                    value={newMemberRole}
                    onChange={(e) => setNewMemberRole(e.target.value)}
                    className="rounded-md border border-line px-2 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                  >
                    {MEMBER_ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                  <Button onClick={addMember} disabled={!newMemberId}>
                    Add
                  </Button>
                </div>

                <ul className="mt-3 divide-y divide-line">
                  {members.map((m) => (
                    <li key={m.user_id} className="flex items-center gap-2 py-2">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-navy-900">
                          {m.full_name || m.email}
                        </p>
                        <p className="truncate text-xs text-muted">{m.email}</p>
                      </div>
                      <select
                        value={m.role}
                        onChange={(e) => updateMember(m.user_id, e.target.value)}
                        className="rounded-md border border-line px-2 py-1.5 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
                      >
                        {MEMBER_ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => removeMember(m.user_id)}
                        aria-label={`Remove ${m.full_name || m.email}`}
                        className="text-muted hover:text-danger"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </li>
                  ))}
                  {members.length === 0 && (
                    <li className="py-2 text-sm text-muted">No members yet.</li>
                  )}
                </ul>
              </Card>
            ) : (
              <Card className="flex h-full items-center justify-center text-center">
                <div>
                  <Building className="mx-auto mb-2 h-8 w-8 text-muted" />
                  <p className="text-sm text-muted">Select a team to manage its members.</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
