import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { SearchResult } from '../api/types'
import { Badge, meetingStatusLabel, meetingStatusVariant } from '../components/ui/Badge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'
import { formatDate } from '../lib/format'

function Highlight({ text, query }: { text: string; query: string }) {
  if (!query) return <>{text}</>
  const lower = text.toLowerCase()
  const idx = lower.indexOf(query.toLowerCase())
  if (idx === -1) return <>{text}</>
  return (
    <>
      {text.slice(0, idx)}
      <mark className="rounded bg-warning/60 px-0.5">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  )
}

function kindLabel(kind: string): string {
  if (kind === 'action_item') return 'Action item'
  if (kind === 'follow_up') return 'Follow-up'
  return 'Meeting'
}

export default function SearchResults() {
  const [params] = useSearchParams()
  const query = params.get('q') ?? ''
  const { teams } = useAuth()
  const navigate = useNavigate()

  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [teamId, setTeamId] = useState('')
  const [kind, setKind] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [tag, setTag] = useState('')
  const [speakerInput, setSpeakerInput] = useState('')
  const [speaker, setSpeaker] = useState('')

  useEffect(() => {
    const t = window.setTimeout(() => setTag(tagInput.trim()), 300)
    return () => window.clearTimeout(t)
  }, [tagInput])

  useEffect(() => {
    const t = window.setTimeout(() => setSpeaker(speakerInput.trim()), 300)
    return () => window.clearTimeout(t)
  }, [speakerInput])

  useEffect(() => {
    const hasQuery = query.trim().length >= 2
    if (!hasQuery && !tag && !speaker) {
      setResults([])
      return
    }
    let cancelled = false
    setLoading(true)
    const p: Record<string, string> = {}
    if (query) p.q = query
    if (teamId) p.team_id = teamId
    if (kind) p.kind = kind
    if (tag) p.tag = tag
    if (speaker) p.speaker = speaker
    api
      .get<SearchResult[]>('/search', { params: p })
      .then(({ data }) => {
        if (!cancelled) setResults(data)
      })
      .catch(() => {
        if (!cancelled) setResults([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [query, teamId, kind, tag, speaker])

  const active = query.trim().length >= 2 || !!tag || !!speaker

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold text-navy-900">Search</h1>
      <p className="text-sm text-muted">
        Search minutes, transcripts, action items, and follow-ups.
      </p>

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
            Type
          </label>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="rounded-md border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
          >
            <option value="">All</option>
            <option value="meeting">Meetings</option>
            <option value="action_item">Action items</option>
            <option value="follow_up">Follow-ups</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
            Tag
          </label>
          <input
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="e.g. RAF"
            className="w-28 rounded-md border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
            Speaker
          </label>
          <input
            value={speakerInput}
            onChange={(e) => setSpeakerInput(e.target.value)}
            placeholder="e.g. Laurie"
            className="w-32 rounded-md border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="mt-6">
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner className="h-6 w-6" />
          </div>
        ) : results.length ? (
          <ul className="space-y-3">
            {results.map((r, i) => (
              <li key={`${r.kind}-${r.meeting_id}-${r.action_item_id ?? ''}-${i}`}>
                <Card
                  className="cursor-pointer p-4 transition-colors hover:bg-canvas/60"
                  onClick={() => navigate(`/meetings/${r.meeting_id}`)}
                >
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="truncate font-semibold text-navy-900">{r.title}</h2>
                    {r.kind === 'meeting' ? (
                      <Badge variant={meetingStatusVariant(r.status)}>
                        {meetingStatusLabel(r.status)}
                      </Badge>
                    ) : (
                      <Badge variant="neutral">{kindLabel(r.kind)}</Badge>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-muted">
                    {r.team_name} · {formatDate(r.date)}
                  </p>
                  {r.speaker && (
                    <p className="text-xs text-muted">Mentioned by {r.speaker}</p>
                  )}
                  <p className="mt-2 text-sm text-navy-800">
                    <Highlight text={r.snippet} query={query} />
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        ) : active ? (
          <Card>
            <EmptyState
              icon={<Search className="h-8 w-8" />}
              title="No matches found"
              description="Try a different keyword, tag, or speaker."
            />
          </Card>
        ) : (
          <Card>
            <EmptyState
              icon={<Search className="h-8 w-8" />}
              title="Search across your meetings"
              description="Type a keyword, or filter by tag or speaker."
            />
          </Card>
        )}
      </div>
    </div>
  )
}
