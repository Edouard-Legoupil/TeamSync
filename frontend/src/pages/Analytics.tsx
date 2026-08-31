import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { AnalyticsData, CountByKey } from '../api/types'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'

function BarRow({ label, count, max }: { label: string; count: number; max: number }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <span className="w-44 shrink-0 truncate text-sm text-navy-800">{label}</span>
      <div className="h-2 min-w-0 flex-1 rounded bg-canvas">
        <div
          className="h-2 rounded bg-primary-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 shrink-0 text-right text-sm text-muted">{count}</span>
    </div>
  )
}

function Section({
  title,
  rows,
  emptyText,
}: {
  title: string
  rows: CountByKey[]
  emptyText: string
}) {
  const max = rows.length ? Math.max(...rows.map((r) => r.count)) : 0
  return (
    <Card>
      <h2 className="mb-3 text-base font-semibold text-navy-900">{title}</h2>
      {rows.length ? (
        <div className="space-y-2">
          {rows.map((row) => (
            <BarRow key={row.key} label={row.label} count={row.count} max={max} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">{emptyText}</p>
      )}
    </Card>
  )
}

export default function Analytics() {
  const { teams } = useAuth()
  const { toast } = useToast()
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [teamId, setTeamId] = useState('')
  const [status, setStatus] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [tag, setTag] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams()
    if (teamId) params.set('team_id', teamId)
    if (status) params.set('status', status)
    if (tag) params.set('tag', tag)
    const qs = params.toString()
    try {
      const { data: d } = await api.get<AnalyticsData>(
        `/analytics${qs ? `?${qs}` : ''}`,
      )
      setData(d)
    } catch {
      toast('Could not load analytics', 'error')
    } finally {
      setLoading(false)
    }
  }, [teamId, status, tag, toast])

  useEffect(() => {
    const t = window.setTimeout(() => setTag(tagInput.trim()), 300)
    return () => window.clearTimeout(t)
  }, [tagInput])

  useEffect(() => {
    load()
  }, [load])

  if (loading && !data) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold text-navy-900">Analytics</h1>
      <p className="text-sm text-muted">Cross-team action-item intelligence.</p>

      {/* Filters */}
      <div className="mt-4 flex flex-wrap items-end gap-2">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
            Team
          </label>
          <select
            value={teamId}
            onChange={(e) => setTeamId(e.target.value)}
            className="rounded-md border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
          >
            <option value="">All teams</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
            Status
          </label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-md border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
          >
            <option value="">Open</option>
            <option value="OPEN">Open only</option>
            <option value="IN_PROGRESS">In progress</option>
            <option value="DONE">Done</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
            Tag
          </label>
          <input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="e.g. RAF, MENA"
            className="rounded-md border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Summary cards */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-2xl font-semibold text-navy-900">{data?.open_count ?? 0}</p>
          <p className="text-sm text-muted">Open action items</p>
        </Card>
        <Card className="p-4">
          <p className="text-2xl font-semibold text-navy-900">{data?.overdue_count ?? 0}</p>
          <p className="text-sm text-muted">Overdue</p>
        </Card>
        <Card className="p-4">
          <p className="text-2xl font-semibold text-navy-900">{data?.by_team.length ?? 0}</p>
          <p className="text-sm text-muted">Teams with items</p>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section
          title="By Theme"
          rows={data?.by_theme ?? []}
          emptyText="No thematic tags."
        />
        <Section
          title="By Region"
          rows={data?.by_region ?? []}
          emptyText="No geographic tags."
        />
        <Section
          title="By Responsible"
          rows={data?.by_assignee ?? []}
          emptyText="No assignees."
        />
        <Section
          title="Top Themes"
          rows={data?.top_themes ?? []}
          emptyText="No themes detected."
        />
      </div>

      <div className="mt-6">
        <Section
          title="Suggested follow-ups by type"
          rows={data?.follow_up_types ?? []}
          emptyText="No follow-ups recorded."
        />
      </div>

      {data && !data.open_count && !data.follow_up_types.length && (
        <EmptyState
          title="No data yet"
          description="Upload and process transcripts to populate analytics."
        />
      )}
    </div>
  )
}
