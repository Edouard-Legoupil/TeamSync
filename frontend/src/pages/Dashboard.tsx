import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FolderOpen, Upload, Users } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useEffectiveTeam } from '../auth/useEffectiveTeam'
import type {
  ActionItem,
  AllDashboardData,
  DashboardData,
  MeetingDetail,
} from '../api/types'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'
import { useProgress } from '../components/ui/Progress'
import { useToast } from '../components/ui/Toast'
import { UploadModal } from '../components/UploadModal'
import { ActionItemsList } from '../components/ActionItemsList'
import { ActionItemModal } from '../components/ActionItemModal'
import { formatDate, weekLabel } from '../lib/format'

const MAX_POLLS = 40 // ~100 seconds at 2.5s intervals

export default function Dashboard() {
  const { teams } = useAuth()
  const { teamId, isAllTeams, notFound } = useEffectiveTeam()
  const navigate = useNavigate()
  const { toast } = useToast()
  const progress = useProgress()

  const [data, setData] = useState<DashboardData | AllDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [selectedItem, setSelectedItem] = useState<ActionItem | null>(null)
  const pollCount = useRef(0)

  const load = useCallback(async () => {
    if (!teamId) return
    setLoading(true)
    try {
      const url = isAllTeams
        ? '/teams/dashboard'
        : `/teams/${teamId}/dashboard`
      const { data: d } = await api.get<DashboardData | AllDashboardData>(url)
      setData(d)
    } catch {
      toast('Could not load dashboard', 'error')
    } finally {
      setLoading(false)
    }
  }, [teamId, isAllTeams, toast])

  useEffect(() => {
    load()
  }, [load])

  function handleUploaded(meetingId: string) {
    setUploadOpen(false)
    setPendingId(meetingId)
    pollCount.current = 0
    progress.start()
    toast('Processing transcript…', 'info')
  }

  useEffect(() => {
    if (!pendingId) return
    let cancelled = false
    const timer = window.setInterval(async () => {
      if (cancelled) return
      pollCount.current += 1
      try {
        const { data: meeting } = await api.get<MeetingDetail>(`/meetings/${pendingId}`)
        if (meeting.status === 'PROCESSED') {
          window.clearInterval(timer)
          setPendingId(null)
          progress.stop()
          toast('Transcript processed. Dashboard updated.', 'success')
          load()
        } else if (meeting.status === 'FAILED') {
          window.clearInterval(timer)
          setPendingId(null)
          progress.stop()
          toast('Processing failed — open the meeting to retry.', 'error')
          load()
        } else if (pollCount.current >= MAX_POLLS) {
          window.clearInterval(timer)
          setPendingId(null)
          progress.stop()
          toast('Still processing — check back shortly.', 'info')
          load()
        }
      } catch {
        // Transient error — keep polling.
      }
    }, 2500)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [pendingId, load, progress, toast])

  if (notFound) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 sm:px-6">
        <EmptyState
          icon={<Users className="h-8 w-8" />}
          title="Team not found"
          description="This team may have been renamed or removed."
        />
      </div>
    )
  }

  if (!teamId) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 sm:px-6">
        <EmptyState
          icon={<Users className="h-8 w-8" />}
          title="No team assigned"
          description="Ask a supervisor or administrator to add you to a team."
        />
      </div>
    )
  }

  if (loading && !data) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  const teamName = isAllTeams
    ? 'All teams'
    : data && 'team_info' in data
      ? data.team_info.name
      : teams.find((t) => t.id === teamId)?.name ?? 'Your team'

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-navy-900">{teamName}</h1>
          <p className="text-sm text-muted">{weekLabel()}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!isAllTeams && (
            <Button onClick={() => setUploadOpen(true)}>
              <Upload className="h-4 w-4" />
              Upload Transcript
            </Button>
          )}
          <Button variant="ghost" onClick={() => navigate('/meetings')}>
            View All Meetings
          </Button>
        </div>
      </div>

      {/* Main grid */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-navy-900">Recent Meetings</h2>
            <button
              onClick={() => navigate('/meetings')}
              className="text-sm font-medium text-primary-700 hover:underline"
            >
              View all
            </button>
          </div>

          {data?.recent_meetings.length ? (
            <ul className="divide-y divide-line">
              {data.recent_meetings.map((meeting) => (
                <li key={meeting.id}>
                  <button
                    onClick={() => navigate(`/meetings/${meeting.id}`)}
                    className="-mx-2 flex w-full items-center justify-between gap-3 rounded px-2 py-3 text-left hover:bg-canvas/60"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-navy-900">
                        {meeting.title}
                      </p>
                      <p className="text-xs text-muted">{formatDate(meeting.date)}</p>
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-1">
                      {meeting.team_name && (
                        <Badge variant="neutral">{meeting.team_name}</Badge>
                      )}
                      {meeting.series_name && (
                        <Badge variant="neutral">{meeting.series_name}</Badge>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={<FolderOpen className="h-8 w-8" />}
              title="No meetings yet"
              description="Upload a transcript to generate your first structured minutes."
              action={
                !isAllTeams ? (
                  <Button onClick={() => setUploadOpen(true)}>Upload Transcript</Button>
                ) : undefined
              }
            />
          )}
        </Card>

        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-navy-900">Open Action Items</h2>
            <button
              onClick={() => navigate('/items')}
              className="text-sm font-medium text-primary-700 hover:underline"
            >
              View all
            </button>
          </div>

          <ActionItemsList
            items={data?.open_action_items ?? []}
            groupByTeam={isAllTeams}
            onSelect={setSelectedItem}
            emptyDescription="New action items will appear here once transcripts are processed."
            emptyAction={
              !isAllTeams ? (
                <Button onClick={() => setUploadOpen(true)}>Upload Transcript</Button>
              ) : undefined
            }
          />
        </div>
      </div>

      {/* Suggested follow-up */}
      <Card className="mt-6">
        <h2 className="text-base font-semibold text-navy-900">Suggested Follow-Up</h2>
        {data?.follow_ups.length ? (
          <ul className="mt-2 space-y-3">
            {data.follow_ups.map((fu) => (
              <li key={fu.id} className="rounded-md border border-line bg-canvas/30 px-3 py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="neutral">{fu.follow_up_type.replace('_', ' ')}</Badge>
                  <span className="text-sm font-medium text-navy-900">{fu.title}</span>
                </div>
                {fu.participants?.length ? (
                  <p className="mt-1 text-xs text-muted">
                    Participants: {fu.participants.join(', ')}
                  </p>
                ) : null}
                {fu.rationale && <p className="text-xs text-muted">{fu.rationale}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-muted">
            No suggested follow-ups yet. Upload a transcript to generate them.
          </p>
        )}
      </Card>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        teamId={isAllTeams ? null : teamId}
        onUploaded={handleUploaded}
      />

      <ActionItemModal
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onSaved={load}
        onOpenMeeting={(item) => navigate(`/meetings/${item.meeting_id}`)}
      />
    </div>
  )
}
