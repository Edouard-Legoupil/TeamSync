import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  CalendarPlus,
  ClipboardList,
  Download,
  ExternalLink,
  ListTodo,
  Mail,
  Pencil,
  RefreshCw,
  Save,
  Settings,
  Trash2,
  X,
} from 'lucide-react'
import { api } from '../api/client'
import { downloadFile } from '../api/download'
import { useAuth } from '../auth/AuthContext'
import type {
  ActionItem,
  MeetingDetail as MeetingDetailType,
  MeetingPermission,
  Member,
  OutlookInfo,
  Series,
} from '../api/types'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import {
  Badge,
  actionStatusLabel,
  actionStatusVariant,
  meetingStatusLabel,
  meetingStatusVariant,
  priorityVariant,
} from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { Modal } from '../components/ui/Modal'
import { Spinner } from '../components/ui/Spinner'
import { useProgress } from '../components/ui/Progress'
import { useToast } from '../components/ui/Toast'
import { EmailDraftModal } from '../components/EmailDraftModal'
import { ActionItemModal } from '../components/ActionItemModal'
import { Markdown } from '../components/Markdown'
import { formatDate, formatDueDate } from '../lib/format'

type Tab = 'minutes' | 'actions' | 'agenda' | 'transcript'

const TABS: { id: Tab; label: string }[] = [
  { id: 'minutes', label: 'Minutes' },
  { id: 'actions', label: 'Action Items' },
  { id: 'agenda', label: 'Suggested Follow-Up' },
  { id: 'transcript', label: 'Transcript' },
]

const LOW_CONFIDENCE = 0.7

export default function MeetingDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { teams } = useAuth()
  const { toast } = useToast()
  const progress = useProgress()

  const [meeting, setMeeting] = useState<MeetingDetailType | null>(null)
  const [items, setItems] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('minutes')
  const [emailOpen, setEmailOpen] = useState(false)
  const [polling, setPolling] = useState(false)

  const [editing, setEditing] = useState(false)
  const [draftMinutes, setDraftMinutes] = useState('')
  const [saving, setSaving] = useState(false)

  const [settingsOpen, setSettingsOpen] = useState(false)
  const [draftTeamId, setDraftTeamId] = useState('')
  const [draftSeriesId, setDraftSeriesId] = useState('')
  const [draftDate, setDraftDate] = useState('')
  const [teamSeries, setTeamSeries] = useState<Series[]>([])
  const [savingSettings, setSavingSettings] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [selectedItem, setSelectedItem] = useState<ActionItem | null>(null)

  const [members, setMembers] = useState<Member[]>([])
  const [permissions, setPermissions] = useState<MeetingPermission[]>([])
  const [newPermUserId, setNewPermUserId] = useState('')
  const [newPermRole, setNewPermRole] = useState('contributor')

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const { data: m } = await api.get<MeetingDetailType>(`/meetings/${id}`)
      setMeeting(m)
      const { data: actionItems } = await api.get<ActionItem[]>(
        `/meetings/${id}/action-items`,
      )
      setItems(actionItems)
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

  async function handleWord() {
    if (!id) return
    try {
      await downloadFile(`/meetings/${id}/export/word`, `meeting-minutes-${id}.docx`)
    } catch {
      toast('Download failed', 'error')
    }
  }

  async function handleTranscript() {
    if (!id || !meeting) return
    try {
      await downloadFile(
        `/meetings/${id}/transcript`,
        meeting.source_filename || `transcript-${id}.txt`,
      )
    } catch {
      toast('Download failed', 'error')
    }
  }

  async function loadSeriesForTeam(teamId: string) {
    try {
      const { data } = await api.get<Series[]>(`/teams/${teamId}/series`)
      setTeamSeries(data)
    } catch {
      setTeamSeries([])
    }
  }

  function openSettings() {
    if (!meeting) return
    setDraftTeamId(meeting.team_id)
    setDraftSeriesId(meeting.series_id ?? '')
    setDraftDate(meeting.date.slice(0, 10))
    setSettingsOpen(true)
    void loadSeriesForTeam(meeting.team_id)
    void loadPermissions()
  }

  async function loadPermissions() {
    if (!id || !meeting) return
    try {
      const [{ data: membersRes }, { data: permsRes }] = await Promise.all([
        api.get<Member[]>(`/teams/${meeting.team_id}/members`),
        api.get<MeetingPermission[]>(`/meetings/${id}/permissions`),
      ])
      setMembers(membersRes)
      setPermissions(permsRes)
    } catch {
      toast('Could not load permissions', 'error')
    }
  }

  async function addPermission() {
    if (!id || !newPermUserId) return
    try {
      await api.post(`/meetings/${id}/permissions`, {
        user_id: newPermUserId,
        role: newPermRole,
      })
      setNewPermUserId('')
      await loadPermissions()
    } catch {
      toast('Could not update permission', 'error')
    }
  }

  async function removePermission(userId: string) {
    if (!id) return
    try {
      await api.delete(`/meetings/${id}/permissions/${userId}`)
      await loadPermissions()
    } catch {
      toast('Could not remove permission', 'error')
    }
  }

  function changeTeam(teamId: string) {
    setDraftTeamId(teamId)
    setDraftSeriesId('')
    void loadSeriesForTeam(teamId)
  }

  async function saveSettings() {
    if (!id || !meeting) return
    setSavingSettings(true)
    try {
      await api.patch(`/meetings/${id}`, {
        team_id: draftTeamId,
        series_id: draftSeriesId || null,
        date: draftDate,
      })
      setSettingsOpen(false)
      await load()
      toast('Meeting updated', 'success')
    } catch {
      toast('Could not update meeting', 'error')
    } finally {
      setSavingSettings(false)
    }
  }

  async function handleDelete() {
    if (!id) return
    if (
      !window.confirm(
        'Delete this meeting and its action items? This cannot be undone.',
      )
    ) {
      return
    }
    setDeleting(true)
    try {
      await api.delete(`/meetings/${id}`)
      toast('Meeting deleted', 'success')
      navigate('/meetings')
    } catch {
      toast('Could not delete meeting', 'error')
      setDeleting(false)
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

  async function refreshFollowUps() {
    if (!id) return
    try {
      await api.post(`/meetings/${id}/follow-ups/refresh`)
      toast('Follow-ups refreshing…', 'info')
      window.setTimeout(() => load(), 2500)
    } catch {
      toast('Could not refresh follow-ups', 'error')
    }
  }

  function startEdit() {
    setDraftMinutes(meeting?.minutes_markdown ?? '')
    setEditing(true)
  }

  async function saveEdit() {
    if (!id) return
    setSaving(true)
    try {
      await api.patch(`/meetings/${id}`, { minutes_markdown: draftMinutes })
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
  const isOwner = meeting.my_role === 'owner'
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
          {!notReady && !editing && isOwner && tab === 'minutes' && (
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
          {isOwner && (
            <Button variant="ghost" onClick={openSettings}>
              <Settings className="h-4 w-4" />
              Settings
            </Button>
          )}
          {isOwner && (
            <Button variant="ghost" onClick={handleDelete} disabled={deleting}>
              <Trash2 className="h-4 w-4" />
              {deleting ? 'Deleting…' : 'Delete'}
            </Button>
          )}
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
                            <button
                              onClick={() => setSelectedItem(item)}
                              className="text-left hover:text-primary-700"
                            >
                              {item.description}
                            </button>
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
                          <td className="px-4 py-3 text-muted">
                            {item.assignee_name ?? 'Unassigned'}
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
                            <Badge variant={actionStatusVariant(item.status)}>
                              {actionStatusLabel(item.status)}
                            </Badge>
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
                {isOwner && !notReady && (
                  <div className="mb-3 flex justify-end">
                    <Button variant="secondary" onClick={refreshFollowUps}>
                      <RefreshCw className="h-4 w-4" />
                      Refresh follow-ups
                    </Button>
                  </div>
                )}
                {meeting.follow_ups.length ? (
                  <ul className="space-y-3">
                    {meeting.follow_ups.map((fu) => (
                      <li
                        key={fu.id}
                        className="rounded-md border border-line bg-white px-4 py-3 shadow-sm"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="neutral">
                            {fu.follow_up_type.replace('_', ' ')}
                          </Badge>
                          <span className="text-sm font-semibold text-navy-900">
                            {fu.title}
                          </span>
                        </div>
                        {fu.issue && (
                          <p className="mt-1 text-sm text-muted">Issue: {fu.issue}</p>
                        )}
                        {fu.participants?.length ? (
                          <p className="mt-1 text-xs text-muted">
                            Participants: {fu.participants.join(', ')}
                          </p>
                        ) : null}
                        {fu.rationale && (
                          <p className="mt-1 text-xs text-muted">Reason: {fu.rationale}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState
                    icon={<ListTodo className="h-8 w-8" />}
                    title="No suggested follow-ups"
                    description="No follow-ups were identified for this meeting."
                  />
                )}
              </div>
            )}

            {tab === 'transcript' && (
              <div className="max-w-[900px]">
                <div className="mb-3 flex justify-end">
                  <Button variant="secondary" onClick={handleTranscript}>
                    <Download className="h-4 w-4" />
                    Download transcript
                  </Button>
                </div>
                <pre className="max-h-[60vh] overflow-y-auto whitespace-pre-wrap rounded-lg border border-line bg-canvas/30 px-4 py-3 font-sans text-sm text-navy-800">
                  {meeting.raw_transcript || 'No transcript text available.'}
                </pre>
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

      <Modal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        title="Meeting Settings"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => setSettingsOpen(false)}
              disabled={savingSettings}
            >
              Cancel
            </Button>
            <Button onClick={saveSettings} disabled={savingSettings}>
              {savingSettings ? 'Saving…' : 'Save'}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Team
            </label>
            <select
              value={draftTeamId}
              onChange={(e) => changeTeam(e.target.value)}
              className="w-full rounded-md border border-line bg-white px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
            >
              {teams.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Meeting series
            </label>
            <select
              value={draftSeriesId}
              onChange={(e) => setDraftSeriesId(e.target.value)}
              className="w-full rounded-md border border-line bg-white px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
            >
              <option value="">No series</option>
              {teamSeries.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Date
            </label>
            <input
              type="date"
              value={draftDate}
              onChange={(e) => setDraftDate(e.target.value)}
              className="w-full rounded-md border border-line bg-white px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
            />
          </div>

          <div className="border-t border-line pt-4">
            <h3 className="mb-2 text-sm font-semibold text-navy-900">Permissions</h3>
            <ul className="mb-3 space-y-1">
              {permissions.length ? (
                permissions.map((p) => (
                  <li
                    key={p.user_id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-navy-800">
                      {p.full_name || p.email}{' '}
                      <span className="text-xs text-muted">({p.role})</span>
                    </span>
                    <button
                      onClick={() => removePermission(p.user_id)}
                      className="text-xs font-medium text-danger hover:underline"
                    >
                      Remove
                    </button>
                  </li>
                ))
              ) : (
                <li className="text-sm text-muted">No permission overrides.</li>
              )}
            </ul>
            <div className="flex gap-2">
              <select
                value={newPermUserId}
                onChange={(e) => setNewPermUserId(e.target.value)}
                className="min-w-0 flex-1 rounded-md border border-line px-2 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
              >
                <option value="">Add member…</option>
                {members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.full_name || m.email}
                  </option>
                ))}
              </select>
              <select
                value={newPermRole}
                onChange={(e) => setNewPermRole(e.target.value)}
                className="rounded-md border border-line px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
              >
                <option value="owner">Owner</option>
                <option value="contributor">Contributor</option>
                <option value="viewer">Viewer</option>
              </select>
              <Button
                variant="secondary"
                onClick={addPermission}
                disabled={!newPermUserId}
              >
                Add
              </Button>
            </div>
          </div>
        </div>
      </Modal>

      <ActionItemModal
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onSaved={load}
        onOpenMeeting={(item) => navigate(`/meetings/${item.meeting_id}`)}
        readOnly={meeting.my_role === 'viewer'}
      />
    </div>
  )
}
