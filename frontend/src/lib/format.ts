// Date and text formatting helpers shared across pages and components.

function parseDate(value: string): Date | null {
  // Date-only strings (YYYY-MM-DD) parse as UTC midnight, which can shift the
  // displayed day in negative-offset timezones. Build a local Date instead.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

const dayFormat: Intl.DateTimeFormatOptions = {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
}

/** Format an ISO date or datetime (e.g. "2026-08-31T08:45:04") as "Aug 31, 2026". */
export function formatDate(value: string): string {
  const parsed = parseDate(value)
  return parsed ? parsed.toLocaleDateString(undefined, dayFormat) : value
}

/** Format an optional due date; null means the item has no deadline. */
export function formatDueDate(value: string | null | undefined): string {
  if (!value) return 'No due date'
  const parsed = parseDate(value)
  return parsed ? parsed.toLocaleDateString(undefined, dayFormat) : value
}

/** Label for the current week, e.g. "Week of Aug 31, 2026" (Monday-based). */
export function weekLabel(now: Date = new Date()): string {
  const day = now.getDay() // 0 = Sunday
  const monday = new Date(now)
  monday.setDate(now.getDate() + (day === 0 ? -6 : 1 - day))
  return `Week of ${monday.toLocaleDateString(undefined, dayFormat)}`
}

/** Two-letter initials from a display name, falling back to the email local part. */
export function initials(
  fullName?: string | null,
  email?: string | null
): string {
  const pick = (value: string): string => {
    const parts = value.split(/[\s._-]+/).filter(Boolean)
    if (parts.length === 0) return ''
    const first = parts[0][0] ?? ''
    const last = parts.length > 1 ? parts[parts.length - 1][0] : ''
    return (first + last).toUpperCase()
  }

  const fromName = pick((fullName ?? '').trim())
  if (fromName) return fromName
  const fromEmail = pick((email ?? '').split('@')[0] ?? '')
  return fromEmail || '?'
}
