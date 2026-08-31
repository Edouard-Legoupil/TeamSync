import { useEffect, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { api } from '../api/client'
import type {
  ActionItem,
  ActionItemComment,
  ActionItemHistoryEntry,
  Member,
} from '../api/types'
import { Button } from './ui/Button'
import { Modal } from './ui/Modal'
import { Spinner } from './ui/Spinner'
import { useToast } from './ui/Toast'

const STATUSES = ['OPEN', 'IN_PROGRESS', 'DONE']
const PRIORITIES = ['HIGH', 'MEDIUM', 'LOW']
const TAG_TYPES = ['thematic', 'organizational', 'geographic', 'process', 'behavior']

const FIELD_LABELS: Record<string, string> = {
  description: 'description',
  assignee: 'assignee',
  due_date: 'due date',
  priority: 'priority',
  status: 'status',
  tags: 'tags',
  completion_notes: 'completion notes',
  completion_links: 'links/documents',
  completion_follow_up: 'follow-up',
}

function formatWhen(value: string): string {
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString()
}

function HistoryLine({ entry }: { entry: ActionItemHistoryEntry }) {
  const when = formatWhen(entry.created_at)
  if (entry.type === 'comment') {
    return (
      <li className="text-xs text-muted">
        <span className="font-medium text-navy-700">{entry.actor_name ?? 'Someone'}</span>{' '}
        commented: <span className="italic">{entry.comment}</span>
        <span className="ml-1 opacity-70">· {when}</span>
      </li>
    )
  }
  const field = FIELD_LABELS[entry.field ?? ''] ?? entry.field ?? 'item'
  return (
    <li className="text-xs text-muted">
      <span className="font-medium text-navy-700">{entry.actor_name ?? 'Someone'}</span>{' '}
      changed {field} from{' '}
      <span className="line-through opacity-70">{entry.from_value || '—'}</span> to{' '}
      <span className="font-medium text-navy-700">{entry.to_value || '—'}</span>
      <span className="ml-1 opacity-70">· {when}</span>
    </li>
  )
}

function CommentNode({
  comment,
  comments,
  onReply,
  depth = 0,
  readOnly = false,
}: {
  comment: ActionItemComment
  comments: ActionItemComment[]
  onReply: (id: string) => void
  depth?: number
  readOnly?: boolean
}) {
  const children = comments.filter((c) => c.parent_id === comment.id)
  return (
    <div className={depth > 0 ? 'ml-4 border-l border-line pl-3' : ''}>
      <p className="text-sm text-navy-800">
        <span className="font-medium text-navy-900">
          {comment.author_name ?? 'Someone'}
        </span>{' '}
        {comment.body}
      </p>
      <div className="mt-0.5 flex items-center gap-3 text-[11px] text-muted">
        <span>{formatWhen(comment.created_at)}</span>
        {!readOnly && (
          <button
            type="button"
            onClick={() => onReply(comment.id)}
            className="font-medium text-primary-700 hover:underline"
          >
            Reply
          </button>
        )}
      </div>
      {children.map((child) => (
        <CommentNode
          key={child.id}
          comment={child}
          comments={comments}
          onReply={onReply}
          depth={depth + 1}
          readOnly={readOnly}
        />
      ))}
    </div>
  )
}

export function ActionItemModal({
  item,
  onClose,
  onSaved,
  onOpenMeeting,
  readOnly = false,
}: {
  item: ActionItem | null
  onClose: () => void
  onSaved: () => void
  onOpenMeeting?: (item: ActionItem) => void
  readOnly?: boolean
}) {
  const { toast } = useToast()
  const [description, setDescription] = useState('')
  const [assigneeId, setAssigneeId] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [priority, setPriority] = useState('MEDIUM')
  const [status, setStatus] = useState('OPEN')
  const [members, setMembers] = useState<Member[]>([])
  const [comments, setComments] = useState<ActionItemComment[]>([])
  const [history, setHistory] = useState<ActionItemHistoryEntry[]>([])
  const [replyToId, setReplyToId] = useState<string | null>(null)
  const [tags, setTags] = useState<{ name: string; type: string }[]>([])
  const [newTagName, setNewTagName] = useState('')
  const [newTagType, setNewTagType] = useState('thematic')
  const [completionNotes, setCompletionNotes] = useState('')
  const [completionLinks, setCompletionLinks] = useState('')
  const [completionFollowUp, setCompletionFollowUp] = useState('')
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!item) return
    setDescription(item.description)
    setAssigneeId(item.assignee_id ?? '')
    setDueDate(item.due_date ?? '')
    setPriority(item.priority)
    setStatus(item.status)
    setTags(item.tags.map((t) => ({ name: t.name, type: t.type })))
    setNewTagName('')
    setNewTagType('thematic')
    setCompletionNotes(item.completion_notes ?? '')
    setCompletionLinks(item.completion_links ?? '')
    setCompletionFollowUp(item.completion_follow_up ?? '')
    setComment('')
    setComments([])
    setHistory([])
    setReplyToId(null)
    setLoading(true)
    Promise.all([
      api.get<Member[]>(`/teams/${item.team_id}/members`),
      api.get<ActionItemComment[]>(`/action-items/${item.id}/comments`),
      api.get<ActionItemHistoryEntry[]>(`/action-items/${item.id}/history`),
    ])
      .then(([membersRes, commentsRes, historyRes]) => {
        setMembers(membersRes.data)
        setComments(commentsRes.data)
        setHistory(historyRes.data.filter((e) => e.type === 'change'))
      })
      .catch(() => toast('Could not load action item details', 'error'))
      .finally(() => setLoading(false))
  }, [item, toast])

  async function save() {
    if (!item) return
    setSaving(true)
    try {
      await api.patch(`/action-items/${item.id}`, {
        description,
        assignee_id: assigneeId || null,
        due_date: dueDate || null,
        priority,
        status,
        tags,
        completion_notes: completionNotes || null,
        completion_links: completionLinks || null,
        completion_follow_up: completionFollowUp || null,
      })
      toast('Action item updated', 'success')
      onSaved()
      onClose()
    } catch {
      toast('Could not update action item', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function addComment() {
    const body = comment.trim()
    if (!item || !body) return
    try {
      await api.post(`/action-items/${item.id}/comments`, {
        body,
        parent_id: replyToId ?? null,
      })
      setComment('')
      setReplyToId(null)
      const [{ data: commentsRes }, { data: historyRes }] = await Promise.all([
        api.get<ActionItemComment[]>(`/action-items/${item.id}/comments`),
        api.get<ActionItemHistoryEntry[]>(`/action-items/${item.id}/history`),
      ])
      setComments(commentsRes)
      setHistory(historyRes.filter((e) => e.type === 'change'))
    } catch {
      toast('Could not add comment', 'error')
    }
  }

  function startReply(commentId: string) {
    setReplyToId(commentId)
  }

  function addTag() {
    const name = newTagName.trim()
    if (!name) return
    if (!tags.some((t) => t.name.toLowerCase() === name.toLowerCase())) {
      setTags((prev) => [...prev, { name, type: newTagType }])
    }
    setNewTagName('')
  }

  function removeTag(name: string) {
    setTags((prev) => prev.filter((t) => t.name !== name))
  }

  return (
    <Modal
      open={!!item}
      onClose={onClose}
      title="Action Item"
      maxWidth="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          {item && onOpenMeeting && (
            <Button
              variant="ghost"
              onClick={() => {
                onClose()
                onOpenMeeting(item)
              }}
              disabled={saving}
            >
              <ExternalLink className="h-4 w-4" />
              Open meeting
            </Button>
          )}
          {!readOnly && (
            <Button onClick={save} disabled={saving || !description.trim()}>
              {saving ? 'Saving…' : 'Save'}
            </Button>
          )}
        </>
      }
    >
      {item && (
        <div className="space-y-5">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              disabled={readOnly}
              className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                Assignee
              </label>
              <select
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value)}
                disabled={readOnly}
                className="w-full rounded-md border border-line bg-white px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
              >
                <option value="">Unassigned</option>
                {members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.full_name || m.email}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                Due date
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                disabled={readOnly}
                className="w-full rounded-md border border-line bg-white px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                disabled={readOnly}
                className="w-full rounded-md border border-line bg-white px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
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
                disabled={readOnly}
                className="w-full rounded-md border border-line bg-white px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s === 'OPEN' ? 'Open' : s === 'IN_PROGRESS' ? 'In progress' : 'Done'}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Tags
            </label>
            <div className="mb-2 flex flex-wrap gap-2">
              {tags.length ? (
                tags.map((tag) => (
                  <span
                    key={tag.name}
                    className="inline-flex items-center gap-1 rounded-full bg-canvas px-2.5 py-0.5 text-xs font-semibold text-muted"
                  >
                    {tag.name}
                    {!readOnly && (
                      <button
                        type="button"
                        onClick={() => removeTag(tag.name)}
                        aria-label={`Remove ${tag.name}`}
                        className="text-muted hover:text-navy-900"
                      >
                        ×
                      </button>
                    )}
                  </span>
                ))
              ) : (
                <span className="text-xs text-muted">No tags yet.</span>
              )}
            </div>
            {!readOnly && (
              <div className="flex gap-2">
                <input
                  value={newTagName}
                  onChange={(e) => setNewTagName(e.target.value)}
                  placeholder="Add tag…"
                  className="min-w-0 flex-1 rounded-md border border-line px-2 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                />
                <select
                  value={newTagType}
                  onChange={(e) => setNewTagType(e.target.value)}
                  className="rounded-md border border-line px-2 py-2 text-sm text-navy-800 focus:border-primary-500 focus:outline-none"
                >
                  {TAG_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <Button
                  variant="secondary"
                  onClick={addTag}
                  disabled={!newTagName.trim()}
                >
                  Add
                </Button>
              </div>
            )}
          </div>

          {(item.source_excerpt ||
            item.source_speaker ||
            item.source_timestamp ||
            item.requester ||
            item.related_participants?.length) && (
            <div className="rounded-md border border-line bg-canvas/30 px-3 py-2">
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">
                Source
              </h4>
              {item.source_excerpt && (
                <p className="text-sm italic text-navy-800">“{item.source_excerpt}”</p>
              )}
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                {item.source_speaker && <span>{item.source_speaker}</span>}
                {item.source_timestamp && <span>minute {item.source_timestamp}</span>}
                {item.attribution_method && <span>via {item.attribution_method}</span>}
                {item.confidence !== null && (
                  <span>{Math.round(item.confidence * 100)}% confidence</span>
                )}
              </div>
              {item.requester && (
                <p className="mt-1 text-xs text-muted">Requester: {item.requester}</p>
              )}
              {item.related_participants?.length ? (
                <p className="text-xs text-muted">
                  Interested: {item.related_participants.join(', ')}
                </p>
              ) : null}
            </div>
          )}

          {status === 'DONE' && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-navy-900">Completion notes</h4>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                  What was done
                </label>
                <textarea
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                  rows={2}
                  disabled={readOnly}
                  className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                  Links / documents
                </label>
                <textarea
                  value={completionLinks}
                  onChange={(e) => setCompletionLinks(e.target.value)}
                  rows={2}
                  disabled={readOnly}
                  className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                  Follow-up recommendations
                </label>
                <textarea
                  value={completionFollowUp}
                  onChange={(e) => setCompletionFollowUp(e.target.value)}
                  rows={2}
                  disabled={readOnly}
                  className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                />
              </div>
            </div>
          )}

          <div>
            <h4 className="mb-2 text-sm font-semibold text-navy-900">Discussion</h4>
            {loading ? (
              <div className="flex justify-center py-4">
                <Spinner className="h-5 w-5" />
              </div>
            ) : comments.length ? (
              <div className="max-h-64 space-y-3 overflow-y-auto rounded-md border border-line bg-canvas/30 px-3 py-2">
                {comments
                  .filter((c) => !c.parent_id)
                  .map((root) => (
                    <CommentNode
                      key={root.id}
                      comment={root}
                      comments={comments}
                      onReply={startReply}
                      readOnly={readOnly}
                    />
                  ))}
              </div>
            ) : (
              <p className="text-sm text-muted">No comments yet.</p>
            )}
          </div>

          {!readOnly && (
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
                {replyToId ? 'Reply' : 'Add comment'}
              </label>
              {replyToId && (
                <div className="mb-1 flex items-center gap-2 text-xs text-muted">
                  Replying to a comment
                  <button
                    type="button"
                    onClick={() => setReplyToId(null)}
                    className="font-medium text-primary-700 hover:underline"
                  >
                    Cancel
                  </button>
                </div>
              )}
              <div className="flex gap-2">
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={2}
                  placeholder={replyToId ? 'Write a reply…' : 'Add a note to this task…'}
                  className="min-w-0 flex-1 rounded-lg border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
                />
                <Button
                  variant="secondary"
                  onClick={addComment}
                  disabled={!comment.trim()}
                  className="self-start"
                >
                  {replyToId ? 'Reply' : 'Add'}
                </Button>
              </div>
            </div>
          )}

          <div>
            <h4 className="mb-2 text-sm font-semibold text-navy-900">History</h4>
            {history.length ? (
              <ul className="max-h-56 space-y-2 overflow-y-auto rounded-md border border-line bg-canvas/30 px-3 py-2">
                {history.map((entry, i) => (
                  <HistoryLine key={i} entry={entry} />
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">No changes yet.</p>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}
