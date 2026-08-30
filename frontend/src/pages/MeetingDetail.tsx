import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  CalendarPlus,
  ClipboardList,
  Download,
  ExternalLink,
  FileText,
  ListTodo,
  Mail,
  Pencil,
  RefreshCw,
  Save,
  X,
} from 'lucide-react'
import { api } from '../api/client'
import { downloadFile } from '../api/download'
import type {
  ActionItem,
  MeetingDetail as MeetingDetailType,
  Member,
  OutlookInfo,
} from '../api/types'
import { Button } from '../components/ui/Button'
import {
  Badge,
  actionStatusLabel,
  actionStatusVariant,
  meetingStatusLabel,
  meetingStatusVariant,
  priorityVariant,
} from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'
import { useProgress } from '../components/ui/Progress'
import { useToast } from '../components/ui/Toast'
import { EmailDraftModal } from '../components/EmailDraftModal'
import { Markdown } from '../components/Markdown'
import { formatDate, formatDueDate } from '../lib/format'

type Tab = 'minutes' | 'actions' | 'agenda'

const TABS: { id: Tab; label: string }[] = [
  { id: 'minutes', label: 'Minutes' },
  { id: 'actions', label: 'Action Items' },
  { id: 'agenda', label: 'Next Agenda' },
]

const STATUS_OPTIONS = ['OPEN', 'IN_PROGRESS', 'DONE']
const LOW_CONFIDENCE = 0.7

export default function MeetingDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const progress = useProgress()

  const [meeting, setMeeting] = useState<MeetingDetailType | null>(null)
  const [items, setItems] = useState<ActionItem[]>([])
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('minutes')
  const [emailOpen, setEmailOpen] = useState(false)
  const [polling, setPolling] = useState(false)

  const [editing, setEditing] = useState(false)
  const [draftMinutes, setDraftMinutes] = useState('')
  const [draftAgenda, setDraftAgenda] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const { data: m } = await api.get<MeetingDetailType>(`/meetings/${id}`)
      setMeeting(m)
      const [{ data: actionItems }, { data: teamMembers }] = await Promise.all([
        api.get<ActionItem[]>(`/meetings/${id}/action-items`),
        api.get<Member[]>(`/teams/${m.team_id}/members`),
      ])
      setItems(actionItems)
      setMembers(teamMembers)
    } catch {
      toast('Could not load meeting', 'error')
    } finally {
      setLoading(false)
    }
  }, [id, toast])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!polling || !id) return
    let cancelled = false
    let tries = 0
    const timer = window.setInterval(async () => {
      if (cancelled) return
      tries += 1
      try {
        const { data: m } = await api.get<MeetingDetailType>(`/meetings/${id}`)
        if (m.status === 'PROCESSED') {
          window.clearInterval(timer)
          setPolling(false)
          progress.stop()
          toast('Transcript processed.', 'success')
          load()
        } else if (m.status === 'FAILED') {
          window.clearInterval(timer)
          setPolling(false)
          progress.stop()
          toast('Processing failed — see error details.', 'error')
          load()
        } else if (tries >= 40) {
          window.clearInterval(timer)
          setPolling(false)
          progress.stop()
          toast('Still processing — check back shortly.', 'info')
        }
      } catch {
        // keep polling on transient errors
      }
    }, 2500)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [polling, id, load, progress, toast])

  async function updateItem(itemId: string, patch: Partial<ActionItem>) {
    try {
      await api.patch(`/action-items/${itemId}`, patch)
      await load()
    } catch {
      toast('Could not update action item', 'error')
    }
  }

  async function handleWord() {
    if (!id) return
    try {
      await downloadFile(`/meetings/${id}/export/word`, `meeting-minutes-${id}.docx`)
    } catch {
      toast('Download failed', 'error')
    }
  }

  async function handleMarkdown() {
    if (!id) return
    try {
      await downloadFile(`/meetings/${id}/export/markdown`, `meeting-minutes-${id}.md`)
    } catch {
      toast('Download failed', 'error')
    }
  }

  async function handleIcs() {
    if (!id) return
    try {
      await downloadFile(`/meetings/${id}/export/ics`, `meeting-${id}.ics`)
    } catch {
      toast('Download failed', 'error')
    }
  }

  async function handleOpenOutlook() {
    if (!id) return
    try {
      const { data } = await api.get<OutlookInfo>(`/meetings/${id}/outlook`)
      window.open(data.calendar_web_url, '_blank', 'noopener')
    } catch {
      toast('Could not open Outlook', 'error')
    }
  }

  async function retryProcessing() {
    if (!id) return
    try {
      await api.post(`/meetings/${id}/process`)
      progress.start()
      setPolling(true)
      toast('Processing started…', 'info')
    } catch {
      toast('Could not start processing', 'error')
    }
  }

  function startEdit() {
    setDraftMinutes(meeting?.minutes_markdown ?? '')
    setDraftAgenda(meeting?.next_agenda_markdown ?? '')
    setEditing(true)
  }

  async function saveEdit() {
    if (!id) return
    setSaving(true)
    try {
      const patch: { minutes_markdown?: string; next_agenda_markdown?: string } = {}
      if (tab === 'minutes') patch.minutes_markdown = draftMinutes
      if (tab === 'agenda') patch.next_agenda_markdown = draftAgenda
      await api.patch(`/meetings/${id}`, patch)
      setEditing(false)
      await load()
      toast('Saved', 'success')
    } catch {
      toast('Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !meeting) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  if (!meeting) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <EmptyState
          icon={<ClipboardList className="h-8 w-8" />}
          title="Meeting not found"
          description="It may have been removed or you may not have access."
          action={<Button onClick={() => navigate('/team')}>Back to Dashboard</Button>}
        />
      </div>
    )
  }

  const isDraft = meeting.status === 'DRAFT'
  const isFailed = meeting.status === 'FAILED'
  const notReady = isDraft || isFailed
  const lowConfidence =
    meeting.confidence !== null && meeting.confidence < LOW_CONFIDENCE

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <button
        onClick={() => navigate('/team')}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-navy-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </button>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold text-navy-900">{meeting.title}</h1>
            <Badge variant={meetingStatusVariant(meeting.status)}>
              {meetingStatusLabel(meeting.status)}
            </Badge>
            {meeting.series_id && <Badge variant="neutral">Series</Badge>}
          </div>
          <p className="mt-1 text-sm text-muted">{formatDate(meeting.date)}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {!notReady && !editing && (
            <Button variant="ghost" onClick={startEdit}>
              <Pencil className="h-4 w-4" />
              Edit
            </Button>
          )}
          {editing && (
            <>
              <Button variant="ghost" onClick={() => setEditing(false)} disabled={saving}>
                <X className="h-4 w-4" />
                Cancel
              </Button>
              <Button variant="primary" onClick={saveEdit} disabled={saving}>
                <Save className="h-4 w-4" />
                {saving ? 'Saving…' : 'Save'}
              </Button>
            </>
          )}
          <Button variant="secondary" onClick={handleWord} disabled={notReady}>
            <Download className="h-4 w-4" />
            Download Word
          </Button>
          <Button variant="ghost" onClick={handleMarkdown} disabled={notReady}>
            <FileText className="h-4 w-4" />
            Markdown
          </Button>
          <Button variant="secondary" onClick={() => setEmailOpen(true)} disabled={notReady}>
            <Mail className="h-4 w-4" />
            Email Draft
          </Button>
          <Button variant="ghost" onClick={handleIcs} disabled={notReady}>
            <CalendarPlus className="h-4 w-4" />
            Add to Calendar
          </Button>
          <Button variant="ghost" onClick={handleOpenOutlook} disabled={notReady}>
            <ExternalLink className="h-4 w-4" />
            Open in Outlook
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-6 flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium ${
              tab === t.id
                ? 'border-primary-600 text-primary-700'
                : 'border-transparent text-muted hover:text-navy-900'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {notReady && tab === 'minutes' ? (
          <Card className="text-center">
            <EmptyState
              icon={
                isFailed ? (
                  <AlertTriangle className="h-8 w-8 text-danger" />
                ) : (
                  <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
                )
              }
              title={isFailed ? 'Processing failed' : 'Processing transcript…'}
              description={
                isFailed
                  ? 'The AI could not process this transcript. You can retry.'
                  : 'The AI is structuring this meeting into minutes, action items, and agenda.'
              }
              action={
                <Button variant="secondary" onClick={retryProcessing}>
                  <RefreshCw className="h-4 w-4" />
                  Retry processing
                </Button>
              }
            />
          </Card>
        ) : (
          <>
            {tab === 'minutes' && (
              <div className="max-w-[800px]">
                {lowConfidence && meeting.confidence !== null && (
                  <div className="mb-4 flex items-center gap-2 rounded-md border border-warning bg-warning-100/70 px-3 py-2 text-sm text-warning-800">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    Low confidence ({Math.round(meeting.confidence * 100)}%) — review
                    these minutes carefully.
                  </div>
                )}
                {editing ? (
                  <textarea
                    value={draftMinutes}
                    onChange={(e) => setDraftMinutes(e.target.value)}
                    rows={18}
                    className="w-full rounded-lg border border-line bg-white px-3 py-2 font-mono text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                  />
                ) : meeting.minutes_markdown ? (
                  <Markdown>{meeting.minutes_markdown}</Markdown>
                ) : (
                  <EmptyState
                    icon={<ClipboardList className="h-8 w-8" />}
                    title="No minutes yet"
                    description="This meeting is still being processed."
                  />
                )}
              </div>
            )}

            {tab === 'actions' && (
              <div className="overflow-x-auto rounded-lg border border-line bg-white">
                {items.length ? (
                  <table className="w-full min-w-[640px] text-sm">
                    <thead>
                      <tr className="border-b border-line bg-canvas/50 text-left text-xs uppercase tracking-wide text-muted">
                        <th className="px-4 py-3 font-semibold">Task</th>
                        <th className="px-4 py-3 font-semibold">Assignee</th>
                        <th className="px-4 py-3 font-semibold">Due date</th>
                        <th className="px-4 py-3 font-semibold">Priority</th>
                        <th className="px-4 py-3 font-semibold">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {items.map((item) => (
                        <tr key={item.id} className="align-top">
                          <td className="px-4 py-3 text-navy-900">
                            {item.description}
                            {item.duplicate_of_id && (
                              <div className="mt-1 flex items-center gap-1.5 text-xs">
                                <Badge variant="blocked">Duplicate</Badge>
                                <button
                                  onClick={() =>
                                    navigate(`/meetings/${item.duplicate_meeting_id}`)
                                  }
                                  className="text-primary-700 hover:underline"
                                >
                                  already tracked
                                </button>
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <select
                              value={item.assignee_id ?? ''}
                              onChange={(e) =>
                                updateItem(item.id, {
                                  assignee_id: e.target.value || null,
                                })
                              }
                              className="w-full max-w-[160px] rounded-md border border-line bg-white px-2 py-1.5 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
                            >
                              <option value="">Unassigned</option>
                              {members.map((m) => (
                                <option key={m.id} value={m.id}>
                                  {m.full_name || m.email}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td className="px-4 py-3 text-muted">
                            {formatDueDate(item.due_date)}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={priorityVariant(item.priority)}>
                              {item.priority}
                            </Badge>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <select
                                value={item.status}
                                onChange={(e) =>
                                  updateItem(item.id, { status: e.target.value })
                                }
                                className="rounded-md border border-line bg-white px-2 py-1.5 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
                              >
                                {STATUS_OPTIONS.map((s) => (
                                  <option key={s} value={s}>
                                    {actionStatusLabel(s)}
                                  </option>
                                ))}
                              </select>
                              <Badge variant={actionStatusVariant(item.status)}>
                                {actionStatusLabel(item.status)}
                              </Badge>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <EmptyState
                    icon={<ListTodo className="h-8 w-8" />}
                    title="No action items"
                    description="No action items were identified in this meeting."
                  />
                )}
              </div>
            )}

            {tab === 'agenda' && (
              <div className="max-w-[800px]">
                {editing ? (
                  <textarea
                    value={draftAgenda}
                    onChange={(e) => setDraftAgenda(e.target.value)}
                    rows={10}
                    className="w-full rounded-lg border border-line bg-white px-3 py-2 font-mono text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                  />
                ) : meeting.next_agenda_markdown ? (
                  <Markdown>{meeting.next_agenda_markdown}</Markdown>
                ) : (
                  <EmptyState
                    icon={<ListTodo className="h-8 w-8" />}
                    title="No upcoming agenda"
                    description="No next-agenda topics were identified."
                  />
                )}
              </div>
            )}
          </>
        )}
      </div>

      <EmailDraftModal
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
        meeting={meeting}
      />
    </div>
  )
}
