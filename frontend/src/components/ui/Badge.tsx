import type { ReactNode } from 'react'

export type BadgeVariant =
  | 'done'
  | 'pending'
  | 'blocked'
  | 'neutral'
  | 'draft'
  | 'processed'
  | 'failed'
  | 'overdue'
  | 'due_soon'
  | 'high'
  | 'medium'
  | 'low'

const STYLES: Record<BadgeVariant, string> = {
  done: 'bg-success-100 text-success-800',
  pending: 'bg-warning-100 text-warning-800',
  blocked: 'bg-danger-100 text-danger-700',
  neutral: 'bg-canvas text-muted',
  draft: 'bg-warning-100 text-warning-800',
  processed: 'bg-success-100 text-success-800',
  failed: 'bg-danger-100 text-danger-700',
  overdue: 'bg-danger-100 text-danger-700',
  due_soon: 'bg-warning-100 text-warning-800',
  high: 'bg-danger-100 text-danger-700',
  medium: 'bg-warning-100 text-warning-800',
  low: 'bg-canvas text-muted',
}

export function Badge({
  variant = 'neutral',
  children,
}: {
  variant?: BadgeVariant
  children: ReactNode
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STYLES[variant]}`}
    >
      {children}
    </span>
  )
}

export function meetingStatusVariant(status: string): BadgeVariant {
  if (status === 'PROCESSED') return 'processed'
  if (status === 'FAILED') return 'failed'
  if (status === 'DRAFT') return 'draft'
  return 'neutral'
}

export function meetingStatusLabel(status: string): string {
  if (status === 'PROCESSED') return 'Processed'
  if (status === 'FAILED') return 'Failed'
  if (status === 'DRAFT') return 'Processing'
  return status
}

export function actionStatusVariant(status: string): BadgeVariant {
  if (status === 'DONE') return 'done'
  if (status === 'IN_PROGRESS') return 'pending'
  return 'neutral'
}

export function actionStatusLabel(status: string): string {
  if (status === 'IN_PROGRESS') return 'In progress'
  if (status === 'DONE') return 'Done'
  return 'Open'
}

export function priorityVariant(priority: string): BadgeVariant {
  if (priority === 'HIGH') return 'high'
  if (priority === 'MEDIUM') return 'medium'
  return 'low'
}
