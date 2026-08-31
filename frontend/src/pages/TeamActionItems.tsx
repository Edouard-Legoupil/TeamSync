import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Copy, Mail, Users } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { useEffectiveTeam } from '../auth/useEffectiveTeam'
import type { ActionItem, Digest } from '../api/types'
import { ActionItemsList } from '../components/ActionItemsList'
import { ActionItemModal } from '../components/ActionItemModal'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { Modal } from '../components/ui/Modal'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'

export default function TeamActionItems() {
  const { teamId, isAllTeams, notFound } = useEffectiveTeam()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [items, setItems] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState<ActionItem | null>(null)
  const [digest, setDigest] = useState<Digest | null>(null)
  const [digestOpen, setDigestOpen] = useState(false)

  const load = useCallback(async () => {
    if (!teamId) return
    setLoading(true)
    try {
      const url = isAllTeams
        ? '/action-items/mine'
        : `/teams/${teamId}/action-items`
      const { data } = await api.get<ActionItem[]>(url)
      setItems(data)
    } catch {
      toast('Could not load action items', 'error')
    } finally {
      setLoading(false)
    }
  }, [teamId, isAllTeams, toast])

  useEffect(() => {
    load()
  }, [load])

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

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-navy-900">Action Items</h1>
          <p className="text-sm text-muted">
            {isAllTeams
              ? 'Open items across all your teams.'
              : 'Open items for this team and its child teams.'}
          </p>
        </div>
        <Button variant="secondary" onClick={openDigest}>
          <Mail className="h-4 w-4" />
          My Digest
        </Button>
      </div>

      <ActionItemsList
        items={items}
        groupByTeam
        onSelect={setSelectedItem}
        emptyDescription={
          isAllTeams
            ? 'No open action items across your teams.'
            : 'No open action items across this team and its child teams.'
        }
      />

      <ActionItemModal
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onSaved={load}
        onOpenMeeting={(item) => navigate(`/meetings/${item.meeting_id}`)}
      />

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
