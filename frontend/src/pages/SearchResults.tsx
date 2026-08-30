import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import { api } from '../api/client'
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
      <mark className="rounded bg-warning/60 px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}

export default function SearchResults() {
  const [params] = useSearchParams()
  const query = params.get('q') ?? ''
  const navigate = useNavigate()
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([])
      return
    }
    let cancelled = false
    setLoading(true)
    api
      .get<SearchResult[]>('/search', { params: { q: query } })
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
  }, [query])

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-semibold text-navy-900">Search</h1>
      <p className="text-sm text-muted">
        {query ? `Results for “${query}”` : 'Search minutes, action items, and agendas.'}
      </p>

      <div className="mt-6">
        {loading ? (
          <div className="flex justify-center py-16">
            <Spinner className="h-6 w-6" />
          </div>
        ) : results.length ? (
          <ul className="space-y-3">
            {results.map((r) => (
              <li key={r.meeting_id}>
                <Card className="cursor-pointer p-4 transition-colors hover:bg-canvas/60" onClick={() => navigate(`/meetings/${r.meeting_id}`)}>
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="truncate font-semibold text-navy-900">{r.title}</h2>
                    <Badge variant={meetingStatusVariant(r.status)}>
                      {meetingStatusLabel(r.status)}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-muted">
                    {r.team_name} · {formatDate(r.date)}
                  </p>
                  <p className="mt-2 text-sm text-navy-800">
                    <Highlight text={r.snippet} query={query} />
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        ) : query.trim().length >= 2 ? (
          <Card>
            <EmptyState
              icon={<Search className="h-8 w-8" />}
              title="No matches found"
              description="Try a different keyword or broader term."
            />
          </Card>
        ) : (
          <Card>
            <EmptyState
              icon={<Search className="h-8 w-8" />}
              title="Type to search"
              description="Search across all meetings you can access."
            />
          </Card>
        )}
      </div>
    </div>
  )
}
