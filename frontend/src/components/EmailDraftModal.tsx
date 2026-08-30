import { useEffect, useState } from 'react'
import { Check, Copy, Download, Mail } from 'lucide-react'
import { api } from '../api/client'
import type { EmailDraft, MeetingDetail } from '../api/types'
import { Button } from './ui/Button'
import { Modal } from './ui/Modal'
import { Spinner } from './ui/Spinner'
import { useToast } from './ui/Toast'

export function EmailDraftModal({
  open,
  onClose,
  meeting,
}: {
  open: boolean
  onClose: () => void
  meeting: MeetingDetail | null
}) {
  const [draft, setDraft] = useState<EmailDraft | null>(null)
  const [loading, setLoading] = useState(false)
  const [to, setTo] = useState('')
  const [copied, setCopied] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    if (!open || !meeting) return
    let cancelled = false
    setLoading(true)
    setDraft(null)
    api
      .post<EmailDraft>(`/meetings/${meeting.id}/email-draft`)
      .then(({ data }) => {
        if (!cancelled) setDraft(data)
      })
      .catch(() => {
        if (!cancelled) toast('Could not generate email draft', 'error')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, meeting, toast])

  async function copyToClipboard() {
    if (!draft) return
    const content = `Subject: ${draft.subject}\n\n${draft.body}`
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      toast('Copied to clipboard', 'success')
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      toast('Copy failed — please copy manually', 'error')
    }
  }

  function downloadTxt() {
    if (!draft) return
    const content = `To: ${to}\nSubject: ${draft.subject}\n\n${draft.body}`
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${meeting?.title ?? 'meeting'}-email-draft.txt`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Email Draft"
      maxWidth="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" onClick={downloadTxt} disabled={!draft}>
            <Download className="h-4 w-4" />
            Download .txt
          </Button>
          <Button variant="secondary" onClick={copyToClipboard} disabled={!draft}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
          <Button
            onClick={() => draft && (window.location.href = draft.mailto)}
            disabled={!draft}
          >
            <Mail className="h-4 w-4" />
            Open in Email Client
          </Button>
        </>
      }
    >
      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner className="h-6 w-6" />
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              To
            </label>
            <input
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="Recipient email(s)"
              className="w-full rounded-md border border-line px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Subject
            </label>
            <input
              value={draft?.subject ?? ''}
              readOnly
              className="w-full rounded-md border border-line bg-canvas/50 px-3 py-2 text-sm text-navy-900"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Body
            </label>
            <pre className="max-h-72 overflow-y-auto whitespace-pre-wrap rounded-md border border-line bg-canvas/50 px-3 py-2 font-sans text-sm text-navy-800">
              {draft?.body ?? ''}
            </pre>
          </div>
        </div>
      )}
    </Modal>
  )
}
