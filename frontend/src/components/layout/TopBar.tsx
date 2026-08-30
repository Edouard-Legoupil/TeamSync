import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Check, ChevronDown, LogOut, Search } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { initials } from '../../lib/format'
import { useClickAway } from '../../lib/useClickAway'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${
    isActive
      ? 'bg-primary-50 text-primary-700'
      : 'text-muted hover:bg-canvas hover:text-navy-900'
  }`

export function TopBar() {
  const { user, teams, currentTeamId, setCurrentTeamId, logout } = useAuth()
  const navigate = useNavigate()

  const [teamOpen, setTeamOpen] = useState(false)
  const [userOpen, setUserOpen] = useState(false)
  const [query, setQuery] = useState('')
  const teamRef = useClickAway<HTMLDivElement>(() => setTeamOpen(false))
  const userRef = useClickAway<HTMLDivElement>(() => setUserOpen(false))

  const currentTeam = teams.find((t) => t.id === currentTeamId)

  function selectTeam(id: string) {
    setCurrentTeamId(id)
    setTeamOpen(false)
    navigate('/team')
  }

  return (
    <header className="sticky top-0 z-40 h-16 border-b border-line bg-white">
      <div className="mx-auto flex h-full max-w-7xl items-center gap-6 px-4 sm:px-6">
        <Link to="/team" className="shrink-0 text-xl font-bold text-primary-600">
          TeamSync
        </Link>

        <nav className="flex items-center gap-1">
          <NavLink to="/team" end className={navClass}>
            Dashboard
          </NavLink>
          <NavLink to="/meetings" className={navClass}>
            Meetings
          </NavLink>
          <NavLink to="/my-items" className={navClass}>
            My Items
          </NavLink>
          <NavLink to="/teams" className={navClass}>
            Teams
          </NavLink>
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
                <span className="max-w-[180px] truncate">
                  {currentTeam?.name ?? 'Select team'}
                </span>
                <ChevronDown className="h-4 w-4 text-muted" />
              </button>

              {teamOpen && (
                <div className="absolute right-0 z-50 mt-1 w-72 rounded-lg border border-line bg-white py-1 shadow-lg">
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
                </div>
              )}
            </div>
          )}

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
