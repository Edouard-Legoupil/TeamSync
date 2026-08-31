import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarDays } from 'lucide-react'
import { api } from '../api/client'
import { ALL_TEAMS, useAuth } from '../auth/AuthContext'
import type { MeetingListRow } from '../api/types'
import { Button } from '../components/ui/Button'
import {
  Badge,
  meetingStatusLabel,
  meetingStatusVariant,
} from '../components/ui/Badge'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import { formatDate } from '../lib/format'

export default function AllMeetings() {
  const { currentTeamId } = useAuth()
  const navigate = useNavigate()
  const { toast } = useToast()

  const [meetings, setMeetings] = useState<MeetingListRow[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    if (!currentTeamId) return
    setLoading(true)
    try {
      const url =
        currentTeamId === ALL_TEAMS ? '/meetings' : `/teams/${currentTeamId}/meetings`
      const { data } = await api.get<MeetingListRow[]>(url)
      setMeetings(data)
    } catch {
      toast('Could not load meetings', 'error')
    } finally {
      setLoading(false)
    }
  }, [currentTeamId, toast])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-navy-900">All Meetings</h1>
        <p className="text-sm text-muted">
          {currentTeamId === ALL_TEAMS
            ? 'Every transcript processed across your teams.'
            : 'Every transcript processed for this team.'}
        </p>
      </div>

      {meetings.length ? (
        <div className="overflow-hidden rounded-lg border border-line bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-line bg-canvas/50 text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-4 py-3 font-semibold">Date</th>
                  <th className="px-4 py-3 font-semibold">Title</th>
                  <th className="px-4 py-3 font-semibold">Team</th>
                  <th className="px-4 py-3 font-semibold">Series</th>
                  <th className="px-4 py-3 font-semibold"># Actions</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {meetings.map((meeting) => (
                  <tr
                    key={meeting.id}
                    onClick={() => navigate(`/meetings/${meeting.id}`)}
                    className="cursor-pointer hover:bg-canvas/60"
                  >
                    <td className="whitespace-nowrap px-4 py-3 text-muted">
                      {formatDate(meeting.date)}
                    </td>
                    <td className="px-4 py-3 font-medium text-navy-900">
                      {meeting.title}
                    </td>
                    <td className="px-4 py-3 text-muted">{meeting.team_name}</td>
                    <td className="px-4 py-3 text-muted">
                      {meeting.series_name ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-muted">{meeting.action_count}</td>
                    <td className="px-4 py-3">
                      <Badge variant={meetingStatusVariant(meeting.status)}>
                        {meetingStatusLabel(meeting.status)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <Card>
          <EmptyState
            icon={<CalendarDays className="h-8 w-8" />}
            title="No meetings yet"
            description="Upload a transcript from the dashboard to get started."
            action={<Button onClick={() => navigate('/team')}>Go to Dashboard</Button>}
          />
        </Card>
      )}
    </div>
  )
}
