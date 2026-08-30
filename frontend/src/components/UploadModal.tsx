import { useEffect, useRef, useState, type DragEvent } from 'react'
import { ClipboardPaste, FileText, Upload, X } from 'lucide-react'
import { api } from '../api/client'
import type { MeetingCreated, Series } from '../api/types'
import { Button } from './ui/Button'
import { Modal } from './ui/Modal'
import { useToast } from './ui/Toast'

const ALLOWED = ['.txt', '.md', '.docx', '.vtt']

type Mode = 'file' | 'paste'

export function UploadModal({
  open,
  onClose,
  teamId,
  onUploaded,
}: {
  open: boolean
  onClose: () => void
  teamId: string | null
  onUploaded: (meetingId: string) => void
}) {
  const [mode, setMode] = useState<Mode>('file')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [series, setSeries] = useState<Series[]>([])
  const [seriesId, setSeriesId] = useState('')
  const [newSeriesName, setNewSeriesName] = useState('')
  const [dragging, setDragging] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()

  useEffect(() => {
    if (!open || !teamId) return
    api
      .get<Series[]>(`/teams/${teamId}/series`)
      .then(({ data }) => setSeries(data))
      .catch(() => setSeries([]))
  }, [open, teamId])

  function reset() {
    setFile(null)
    setText('')
    setSeriesId('')
    setNewSeriesName('')
    setError(null)
    setDragging(false)
  }

  function handleClose() {
    if (submitting) return
    reset()
    onClose()
  }

  function handleFile(f: File | null | undefined) {
    setError(null)
    if (!f) return
    const ext = '.' + (f.name.split('.').pop()?.toLowerCase() ?? '')
    if (!ALLOWED.includes(ext)) {
      setError('Please choose a .txt, .vtt, or .docx file.')
      return
    }
    setFile(f)
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  async function process() {
    if (!teamId) return
    if (mode === 'file' && !file) return
    if (mode === 'paste' && !text.trim()) return

    setSubmitting(true)
    setError(null)
    try {
      let sid: string | null = null
      if (seriesId === '__new__') {
        const { data } = await api.post<Series>('/series', {
          team_id: teamId,
          name: newSeriesName.trim(),
        })
        sid = data.id
      } else if (seriesId) {
        sid = seriesId
      }

      if (mode === 'file') {
        const form = new FormData()
        form.append('team_id', teamId)
        form.append('file', file as File)
        if (sid) form.append('series_id', sid)
        const { data } = await api.post<MeetingCreated>('/meetings/upload', form)
        reset()
        onUploaded(data.meeting_id)
      } else {
        const { data } = await api.post<MeetingCreated>('/meetings/import', {
          team_id: teamId,
          text: text.trim(),
          series_id: sid,
        })
        reset()
        onUploaded(data.meeting_id)
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response
        ?.data?.detail
      setError(detail ?? 'Upload failed. Please try again.')
      toast('Upload failed', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Upload Transcript"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={process}
            disabled={submitting || (mode === 'file' ? !file : !text.trim())}
          >
            {submitting ? 'Processing…' : 'Process'}
          </Button>
        </>
      }
    >
      {/* Mode tabs */}
      <div className="mb-4 flex gap-1 rounded-md bg-canvas p-1">
        <button
          onClick={() => setMode('file')}
          className={`flex-1 rounded px-3 py-2 text-sm font-medium ${
            mode === 'file' ? 'bg-white text-navy-900 shadow-sm' : 'text-muted'
          }`}
        >
          File
        </button>
        <button
          onClick={() => setMode('paste')}
          className={`flex-1 rounded px-3 py-2 text-sm font-medium ${
            mode === 'paste' ? 'bg-white text-navy-900 shadow-sm' : 'text-muted'
          }`}
        >
          Paste
        </button>
      </div>

      {mode === 'file' ? (
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragging ? 'border-primary-500 bg-primary-50' : 'border-line bg-canvas/50'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".txt,.md,.docx,.vtt"
            className="hidden"
            onChange={(e) => handleFile(e.target.files?.[0])}
          />
          <Upload className="mb-3 h-8 w-8 text-primary-600" />
          <p className="text-sm font-medium text-navy-900">
            Drag and drop your transcript here
          </p>
          <p className="mt-1 text-xs text-muted">
            or click to browse — .txt, .vtt, or .docx
          </p>
        </div>
      ) : (
        <div>
          <ClipboardPaste className="mb-2 h-5 w-5 text-primary-600" />
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={10}
            placeholder="Paste your transcript text here…"
            className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
          />
        </div>
      )}

      {mode === 'file' && file && (
        <div className="mt-4 flex items-center gap-3 rounded-lg border border-line bg-white px-4 py-3">
          <FileText className="h-5 w-5 shrink-0 text-primary-600" />
          <span className="min-w-0 flex-1 truncate text-sm text-navy-800">
            {file.name}
          </span>
          <button
            onClick={() => setFile(null)}
            aria-label="Remove file"
            className="text-muted hover:text-navy-900"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Series */}
      <div className="mt-4 space-y-2">
        <label className="block text-xs font-semibold uppercase tracking-wide text-muted">
          Meeting series (optional)
        </label>
        <select
          value={seriesId}
          onChange={(e) => setSeriesId(e.target.value)}
          className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
        >
          <option value="">No series</option>
          {series.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
          <option value="__new__">+ New series…</option>
        </select>
        {seriesId === '__new__' && (
          <input
            value={newSeriesName}
            onChange={(e) => setNewSeriesName(e.target.value)}
            placeholder="Series name (e.g. Weekly Coordination)"
            className="w-full rounded-md border border-line px-3 py-2 text-sm text-navy-900 focus:border-primary-500 focus:outline-none"
          />
        )}
      </div>

      {error && <p className="mt-3 text-sm text-danger">{error}</p>}
    </Modal>
  )
}
