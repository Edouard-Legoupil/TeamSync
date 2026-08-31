import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Bell, Check, ChevronDown, LogOut, Plus, Search } from 'lucide-react'
import { api } from '../../api/client'
import { ALL_TEAMS, useAuth } from '../../auth/AuthContext'
import type { Notification, Team } from '../../api/types'
import { initials } from '../../lib/format'
import { useClickAway } from '../../lib/useClickAway'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${
    isActive
      ? 'bg-primary-50 text-primary-700'
      : 'text-muted hover:bg-canvas hover:text-navy-900'
  }`

export function TopBar() {
  const { user, teams, currentTeamId, setCurrentTeamId, logout, refresh } = useAuth()
  const navigate = useNavigate()

  const [teamOpen, setTeamOpen] = useState(false)
  const [userOpen, setUserOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [newSpaceOpen, setNewSpaceOpen] = useState(false)
  const [newSpaceName, setNewSpaceName] = useState('')
  const [newSpaceKind, setNewSpaceKind] = useState('personal')
  const [query, setQuery] = useState('')
  const teamRef = useClickAway<HTMLDivElement>(() => setTeamOpen(false))
  const userRef = useClickAway<HTMLDivElement>(() => setUserOpen(false))
  const notifRef = useClickAway<HTMLDivElement>(() => setNotifOpen(false))

  useEffect(() => {
    let active = true
    api
      .get<{ count: number }>('/notifications/unread-count')
      .then(({ data }) => {
        if (active) setUnreadCount(data.count)
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])

  async function toggleNotifications() {
    const next = !notifOpen
    setNotifOpen(next)
    if (next) {
      try {
        const { data } = await api.get<Notification[]>('/notifications')
        setNotifications(data)
        setUnreadCount(data.filter((n) => !n.read).length)
      } catch {
        // ignore
      }
    }
  }

  async function openNotification(n: Notification) {
    setNotifOpen(false)
    if (!n.read) {
      try {
        await api.post(`/notifications/${n.id}/read`)
        setUnreadCount((c) => Math.max(0, c - 1))
      } catch {
        // ignore
      }
    }
    if (n.meeting_id) navigate(`/meetings/${n.meeting_id}`)
  }

  async function markAllRead() {
    try {
      await api.post('/notifications/read-all')
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
      setUnreadCount(0)
    } catch {
      // ignore
    }
  }

  const currentTeam = teams.find((t) => t.id === currentTeamId)
  const scopeLabel =
    currentTeamId === ALL_TEAMS ? 'All teams' : currentTeam?.name ?? 'Select team'
  const canSeeAnalytics =
    user?.role === 'SUPER_ADMIN' ||
    user?.role === 'SUPERVISOR' ||
    teams.some((t) => t.is_manager)

  function selectTeam(id: string) {
    setCurrentTeamId(id)
    setTeamOpen(false)
    navigate('/team')
  }

  async function createSpace() {
    const name = newSpaceName.trim()
    if (!name) return
    try {
      const { data } = await api.post<Team>('/teams', { name, kind: newSpaceKind })
      setNewSpaceName('')
      setNewSpaceOpen(false)
      setTeamOpen(false)
      await refresh()
      setCurrentTeamId(data.id)
      navigate('/team')
    } catch {
      // ignore — no toast context here
    }
  }

  return (
    <header className="sticky top-0 z-40 h-16 border-b border-line bg-white">
      <div className="mx-auto flex h-full max-w-7xl items-center gap-6 px-4 sm:px-6">
        <Link to="/team" className="flex shrink-0 flex-col leading-none">
          <span className="text-xl font-bold text-primary-600">TeamSync</span>
          <span className="mt-0.5 text-[10px] italic text-muted">
            Verba volant, scripta manent
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          <NavLink to="/team" end className={navClass}>
            Dashboard
          </NavLink>
          <NavLink to="/meetings" className={navClass}>
            Meetings
          </NavLink>
          <NavLink to="/items" className={navClass}>
            Action Items
          </NavLink>
          {canSeeAnalytics && (
            <NavLink to="/analytics" className={navClass}>
              Analytics
            </NavLink>
          )}
          {user?.role === 'SUPER_ADMIN' && (
            <NavLink to="/admin" className={navClass}>
              Admin
            </NavLink>
          )}
        </nav>

        <form
          className="relative ml-2 hidden max-w-xs flex-1 md:block"
          onSubmit={(e) => {
            e.preventDefault()
            const q = query.trim()
            if (q) navigate(`/search?q=${encodeURIComponent(q)}`)
          }}
        >
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search meetings…"
            className="w-full rounded-md border border-line bg-canvas/50 py-2 pl-9 pr-3 text-sm text-navy-900 focus:border-primary-500 focus:bg-white focus:outline-none"
          />
        </form>

        <div className="ml-auto flex items-center gap-3">
          {teams.length > 1 && (
            <div className="relative" ref={teamRef}>
              <button
                onClick={() => setTeamOpen((v) => !v)}
                className="flex min-h-[40px] items-center gap-2 rounded-md border border-line bg-white px-3 text-sm text-navy-800 hover:bg-canvas"
              >
                <span className="max-w-[180px] truncate">{scopeLabel}</span>
                <ChevronDown className="h-4 w-4 text-muted" />
              </button>

              {teamOpen && (
                <div className="absolute right-0 z-50 mt-1 w-72 rounded-lg border border-line bg-white py-1 shadow-lg">
                  <button
                    onClick={() => selectTeam(ALL_TEAMS)}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-navy-800 hover:bg-canvas"
                  >
                    <span className="truncate">All teams</span>
                    {currentTeamId === ALL_TEAMS && (
                      <Check className="ml-auto h-4 w-4 shrink-0 text-primary-600" />
                    )}
                  </button>
                  {teams.map((team) => (
                    <button
                      key={team.id}
                      onClick={() => selectTeam(team.id)}
                      className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-navy-800 hover:bg-canvas"
                    >
                      <span className="truncate">{team.name}</span>
                      {team.id === currentTeamId && (
                        <Check className="ml-auto h-4 w-4 shrink-0 text-primary-600" />
                      )}
                    </button>
                  ))}
                  <div className="border-t border-line">
                    {newSpaceOpen ? (
                      <div className="px-3 py-2">
                        <input
                          value={newSpaceName}
                          onChange={(e) => setNewSpaceName(e.target.value)}
                          placeholder="Space name…"
                          className="w-full rounded-md border border-line px-2 py-1.5 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                        />
                        <div className="mt-2 flex gap-2">
                          <select
                            value={newSpaceKind}
                            onChange={(e) => setNewSpaceKind(e.target.value)}
                            className="min-w-0 flex-1 rounded-md border border-line px-2 py-1.5 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
                          >
                            <option value="personal">Personal</option>
                            <option value="project">Project</option>
                            <option value="donor">Donor</option>
                            <option value="operation">Operation</option>
                            <option value="team">Team</option>
                          </select>
                          <button
                            onClick={createSpace}
                            disabled={!newSpaceName.trim()}
                            className="rounded-md bg-primary-600 px-2.5 py-1.5 text-sm font-medium text-white disabled:opacity-50"
                          >
                            Create
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => setNewSpaceOpen(true)}
                        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-primary-700 hover:bg-canvas"
                      >
                        <Plus className="h-4 w-4" />
                        New space…
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="relative" ref={notifRef}>
            <button
              onClick={toggleNotifications}
              aria-label="Notifications"
              className="relative flex h-10 w-10 items-center justify-center rounded-md text-muted hover:bg-canvas hover:text-navy-900"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {notifOpen && (
              <div className="absolute right-0 z-50 mt-1 w-80 rounded-lg border border-line bg-white shadow-lg">
                <div className="flex items-center justify-between border-b border-line px-4 py-2">
                  <span className="text-sm font-semibold text-navy-900">Notifications</span>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="text-xs font-medium text-primary-700 hover:underline"
                    >
                      Mark all read
                    </button>
                  )}
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notifications.length ? (
                    notifications.map((n) => (
                      <button
                        key={n.id}
                        onClick={() => openNotification(n)}
                        className="flex w-full items-start gap-2 border-b border-line px-4 py-2.5 text-left text-sm last:border-b-0 hover:bg-canvas/60"
                      >
                        <span
                          className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? 'bg-transparent' : 'bg-primary-500'}`}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block text-navy-800">{n.text}</span>
                          {n.actor_name && (
                            <span className="block text-xs text-muted">{n.actor_name}</span>
                          )}
                        </span>
                      </button>
                    ))
                  ) : (
                    <p className="px-4 py-6 text-center text-sm text-muted">
                      No notifications.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="relative" ref={userRef}>
            <button
              onClick={() => setUserOpen((v) => !v)}
              aria-label="Account menu"
              className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-navy-600 text-sm font-semibold text-white hover:bg-navy-700"
            >
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : (
                initials(user?.full_name, user?.email)
              )}
            </button>

            {userOpen && (
              <div className="absolute right-0 z-50 mt-1 w-60 rounded-lg border border-line bg-white py-1 shadow-lg">
                <div className="border-b border-line px-4 py-3">
                  <p className="truncate text-sm font-semibold text-navy-900">
                    {user?.full_name || user?.email}
                  </p>
                  <p className="truncate text-xs text-muted">{user?.email}</p>
                </div>
                <button
                  onClick={() => {
                    setUserOpen(false)
                    void logout()
                  }}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-navy-800 hover:bg-canvas"
                >
                  <LogOut className="h-4 w-4 text-muted" />
                  Log out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
