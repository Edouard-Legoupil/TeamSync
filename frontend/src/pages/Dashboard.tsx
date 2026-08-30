import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckSquare, FolderOpen, Upload, Users } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { ActionItem, DashboardData, MeetingDetail } from '../api/types'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import {
  Badge,
  meetingStatusLabel,
  meetingStatusVariant,
  priorityVariant,
} from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'
import { useProgress } from '../components/ui/Progress'
import { useToast } from '../components/ui/Toast'
import { UploadModal } from '../components/UploadModal'
import { Markdown } from '../components/Markdown'
import { formatDate, formatDueDate, weekLabel } from '../lib/format'

const MAX_POLLS = 40 // ~100 seconds at 2.5s intervals

export default function Dashboard() {
  const { currentTeamId, teams } = useAuth()
  const navigate = useNavigate()
  const { toast } = useToast()
  const progress = useProgress()

  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const pollCount = useRef(0)

  const load = useCallback(async () => {
    if (!currentTeamId) return
    setLoading(true)
    try {
      const { data: d } = await api.get<DashboardData>(
        `/teams/${currentTeamId}/dashboard`,
      )
      setData(d)
    } catch {
      toast('Could not load dashboard', 'error')
    } finally {
      setLoading(false)
    }
  }, [currentTeamId, toast])

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

  async function toggleDone(item: ActionItem) {
    try {
      await api.patch(`/action-items/${item.id}`, { status: 'DONE' })
      await load()
    } catch {
      toast('Could not update action item', 'error')
    }
  }

  if (!currentTeamId) {
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

  const teamName =
    data?.team_info.name ??
    teams.find((t) => t.id === currentTeamId)?.name ??
    'Your team'

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-navy-900">{teamName}</h1>
          <p className="text-sm text-muted">{weekLabel()}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setUploadOpen(true)}>
            <Upload className="h-4 w-4" />
            Upload Transcript
          </Button>
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
                    <Badge variant={meetingStatusVariant(meeting.status)}>
                      {meetingStatusLabel(meeting.status)}
                    </Badge>
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
                <Button onClick={() => setUploadOpen(true)}>Upload Transcript</Button>
              }
            />
          )}
        </Card>

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-navy-900">Open Action Items</h2>
            <span className="text-sm text-muted">
              {data?.open_action_items.length ?? 0}
            </span>
          </div>

          {data?.open_action_items.length ? (
            <ul className="divide-y divide-line">
              {data.open_action_items.map((item) => (
                <li key={item.id} className="flex items-start gap-3 py-3">
                  <input
                    type="checkbox"
                    onChange={() => toggleDone(item)}
                    className="mt-1 h-4 w-4 cursor-pointer rounded border-line accent-primary-600"
                    aria-label={`Mark "${item.description}" as done`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-navy-900">{item.description}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                      <span>{item.assignee_name ?? 'Unassigned'}</span>
                      <span aria-hidden>·</span>
                      <span>{formatDueDate(item.due_date)}</span>
                      {item.overdue && <Badge variant="overdue">Overdue</Badge>}
                      {item.due_soon && <Badge variant="due_soon">Due soon</Badge>}
                      <Badge variant={priorityVariant(item.priority)}>
                        {item.priority}
                      </Badge>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={<CheckSquare className="h-8 w-8" />}
              title="No open action items. Great job!"
              description="New action items will appear here once transcripts are processed."
            />
          )}
        </Card>
      </div>

      {/* Next agenda preview */}
      <Card className="mt-6">
        <h2 className="text-base font-semibold text-navy-900">Next Agenda</h2>
        {data?.next_agenda_preview ? (
          <Markdown className="mt-2">{data.next_agenda_preview}</Markdown>
        ) : (
          <p className="mt-2 text-sm text-muted">
            No upcoming agenda. Upload a transcript to generate one.
          </p>
        )}
      </Card>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        teamId={currentTeamId}
        onUploaded={handleUploaded}
      />
    </div>
  )
}
