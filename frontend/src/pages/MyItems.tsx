import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckSquare, Copy, Mail } from 'lucide-react'
import { api } from '../api/client'
import type { ActionItemWithContext, Digest } from '../api/types'
import { Badge, priorityVariant } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Modal } from '../components/ui/Modal'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import { formatDueDate } from '../lib/format'

export default function MyItems() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [items, setItems] = useState<ActionItemWithContext[]>([])
  const [loading, setLoading] = useState(true)
  const [digest, setDigest] = useState<Digest | null>(null)
  const [digestOpen, setDigestOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get<ActionItemWithContext[]>('/action-items/mine')
      setItems(data)
    } catch {
      toast('Could not load your action items', 'error')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  async function toggleDone(id: string) {
    try {
      await api.patch(`/action-items/${id}`, { status: 'DONE' })
      await load()
    } catch {
      toast('Could not update action item', 'error')
    }
  }

  async function openDigest() {
    try {
      const { data } = await api.get<Digest>('/reports/my-digest')
      setDigest(data)
      setDigestOpen(true)
    } catch {
      toast('Could not build digest', 'error')
    }
  }

  async function copyDigest() {
    if (!digest) return
    try {
      await navigator.clipboard.writeText(`${digest.subject}\n\n${digest.body}`)
      toast('Copied to clipboard', 'success')
    } catch {
      toast('Copy failed', 'error')
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-navy-900">My Action Items</h1>
          <p className="text-sm text-muted">Open items across all your teams.</p>
        </div>
        <Button variant="secondary" onClick={openDigest}>
          <Mail className="h-4 w-4" />
          My Digest
        </Button>
      </div>

      <div className="mt-6">
        {items.length ? (
          <div className="divide-y divide-line overflow-hidden rounded-lg border border-line bg-white shadow-sm">
            {items.map((item) => (
              <div key={item.id} className="flex items-start gap-3 px-4 py-3">
                <input
                  type="checkbox"
                  onChange={() => toggleDone(item.id)}
                  className="mt-1 h-4 w-4 cursor-pointer rounded border-line accent-primary-600"
                  aria-label={`Mark "${item.description}" as done`}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-navy-900">{item.description}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {item.team_name} · {item.meeting_title}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                    <span className="text-muted">{item.assignee_name ?? 'Unassigned'}</span>
                    <span className="text-muted">·</span>
                    <span className="text-muted">{formatDueDate(item.due_date)}</span>
                    {item.overdue && <Badge variant="overdue">Overdue</Badge>}
                    {item.due_soon && <Badge variant="due_soon">Due soon</Badge>}
                    <Badge variant={priorityVariant(item.priority)}>{item.priority}</Badge>
                  </div>
                </div>
                <button
                  onClick={() => navigate(`/meetings/${item.meeting_id}`)}
                  className="shrink-0 text-xs font-medium text-primary-700 hover:underline"
                >
                  Open
                </button>
              </div>
            ))}
          </div>
        ) : (
          <Card>
            <EmptyState
              icon={<CheckSquare className="h-8 w-8" />}
              title="No open action items. Great job!"
              description="Items assigned to you will appear here."
            />
          </Card>
        )}
      </div>

      <Modal
        open={digestOpen}
        onClose={() => setDigestOpen(false)}
        title="My Digest"
        footer={
          <>
            <Button variant="ghost" onClick={copyDigest}>
              <Copy className="h-4 w-4" />
              Copy
            </Button>
            <Button onClick={() => digest && (window.location.href = digest.mailto)}>
              <Mail className="h-4 w-4" />
              Open in Email
            </Button>
          </>
        }
      >
        <p className="mb-2 text-sm font-semibold text-navy-900">{digest?.subject}</p>
        <pre className="max-h-80 overflow-y-auto whitespace-pre-wrap rounded-md border border-line bg-canvas/50 px-3 py-2 font-sans text-sm text-navy-800">
          {digest?.body ?? 'No open action items. Great job!'}
        </pre>
      </Modal>
    </div>
  )
}
