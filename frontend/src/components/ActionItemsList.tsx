import type { ReactNode } from 'react'
import { CheckSquare } from 'lucide-react'
import type { ActionItem } from '../api/types'
import { formatDueDate } from '../lib/format'
import { Badge, priorityVariant } from './ui/Badge'
import { EmptyState } from './ui/EmptyState'

interface SeriesGroup {
  key: string
  label: string
  items: ActionItem[]
}

interface Section {
  key: string
  label: string
  groups: SeriesGroup[]
}

const TAG_COLORS: Record<string, string> = {
  thematic: 'bg-primary-50 text-primary-700',
  organizational: 'bg-canvas text-navy-900',
  geographic: 'bg-success-100 text-success-800',
  process: 'bg-warning-100 text-warning-800',
  behavior: 'bg-danger-100 text-danger-700',
}

function seriesKeyOf(item: ActionItem): { key: string; label: string } {
  return item.series_name
    ? { key: item.series_name, label: item.series_name }
    : { key: '', label: 'No series' }
}

function buildSections(items: ActionItem[], groupByTeam: boolean): Section[] {
  const byTeam = new Map<string, ActionItem[]>()
  for (const item of items) {
    const teamKey = groupByTeam ? item.team_name || 'Unnamed team' : ''
    const bucket = byTeam.get(teamKey) ?? []
    bucket.push(item)
    byTeam.set(teamKey, bucket)
  }

  const sections: Section[] = []
  for (const teamKey of [...byTeam.keys()].sort((a, b) => a.localeCompare(b))) {
    const bySeries = new Map<string, ActionItem[]>()
    for (const item of byTeam.get(teamKey) ?? []) {
      const { key } = seriesKeyOf(item)
      const bucket = bySeries.get(key) ?? []
      bucket.push(item)
      bySeries.set(key, bucket)
    }
    const groups = [...bySeries.entries()]
      .map(([key, groupItems]) => ({
        key,
        label: key || 'No series',
        items: groupItems,
      }))
      .sort((a, b) =>
        a.label === 'No series'
          ? 1
          : b.label === 'No series'
            ? -1
            : a.label.localeCompare(b.label),
      )
    sections.push({ key: teamKey, label: teamKey, groups })
  }
  return sections
}

function ItemRow({
  item,
  onSelect,
}: {
  item: ActionItem
  onSelect?: (item: ActionItem) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(item)}
      className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-canvas/40"
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm text-navy-900 hover:text-primary-700">
          {item.description}
        </p>
        {item.meeting_title && (
          <p className="mt-0.5 text-xs text-muted">{item.meeting_title}</p>
        )}
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
          {item.assignee_name && <span>{item.assignee_name}</span>}
          <span>{formatDueDate(item.due_date)}</span>
          {item.overdue && <Badge variant="overdue">Overdue</Badge>}
          {item.due_soon && <Badge variant="due_soon">Due soon</Badge>}
          <Badge variant={priorityVariant(item.priority)}>{item.priority}</Badge>
          {item.tags.map((tag) => (
            <span
              key={tag.id}
              className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${TAG_COLORS[tag.type] ?? 'bg-canvas text-muted'}`}
            >
              {tag.name}
            </span>
          ))}
        </div>
      </div>
    </button>
  )
}

function Box({
  title,
  items,
  groupByTeam,
  onSelect,
}: {
  title: string
  items: ActionItem[]
  groupByTeam: boolean
  onSelect?: (item: ActionItem) => void
}) {
  if (items.length === 0) return null

  const sections = buildSections(items, groupByTeam)
  return (
    <div className="rounded-lg border border-line bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <h3 className="text-sm font-semibold text-navy-900">{title}</h3>
        <span className="rounded-full bg-canvas px-2 py-0.5 text-xs font-medium text-muted">
          {items.length}
        </span>
      </div>
      <div>
        {sections.map((section, sectionIndex) => (
          <div
            key={section.key || `section-${sectionIndex}`}
            className={sectionIndex > 0 ? 'border-t border-line' : ''}
          >
            {groupByTeam && (
              <div className="bg-canvas/50 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted">
                {section.label}
              </div>
            )}
            {section.groups.map((group, groupIndex) => (
              <div key={group.key || `group-${groupIndex}`}>
                <div className="px-4 py-1.5 text-xs font-medium text-muted">
                  {group.label}
                </div>
                <div className="divide-y divide-line">
                  {group.items.map((item) => (
                    <ItemRow key={item.id} item={item} onSelect={onSelect} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function ActionItemsList({
  items,
  groupByTeam = false,
  onSelect,
  emptyTitle = 'No open action items. Great job!',
  emptyDescription = 'New action items will appear here once transcripts are processed.',
  emptyAction,
}: {
  items: ActionItem[]
  groupByTeam?: boolean
  onSelect?: (item: ActionItem) => void
  emptyTitle?: string
  emptyDescription?: string
  emptyAction?: ReactNode
}) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<CheckSquare className="h-8 w-8" />}
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
      />
    )
  }

  const assigned = items.filter((item) => item.assignee_name != null)
  const unassigned = items.filter((item) => item.assignee_name == null)

  return (
    <div className="space-y-4">
      <Box title="Assigned" items={assigned} groupByTeam={groupByTeam} onSelect={onSelect} />
      <Box
        title="Unassigned"
        items={unassigned}
        groupByTeam={groupByTeam}
        onSelect={onSelect}
      />
    </div>
  )
}
