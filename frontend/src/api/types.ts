export interface User {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  avatar_url: string | null
}

export interface Team {
  id: string
  name: string
  description: string | null
  role: string
  is_manager: boolean
}

export interface TeamInfo {
  id: string
  name: string
  description: string | null
}

export interface Member {
  id: string
  full_name: string
  email: string
}

export interface MeetingSummary {
  id: string
  title: string
  date: string
  status: string
}

export interface ActionItem {
  id: string
  meeting_id: string
  description: string
  assignee_id: string | null
  assignee_name: string | null
  due_date: string | null
  priority: string
  status: string
  source_markdown?: string | null
  overdue: boolean
  due_soon: boolean
  duplicate_of_id: string | null
  duplicate_of_title: string | null
  duplicate_meeting_id: string | null
  duplicate_meeting_title: string | null
}

export interface DashboardData {
  team_info: TeamInfo
  recent_meetings: MeetingSummary[]
  open_action_items: ActionItem[]
  next_agenda_preview: string
}

export interface MeetingDetail {
  id: string
  title: string
  date: string
  team_id: string
  organizer_id: string | null
  status: string
  series_id: string | null
  minutes_markdown: string | null
  action_items_markdown: string | null
  next_agenda_markdown: string | null
  confidence: number | null
}

export interface MeetingListRow {
  id: string
  title: string
  date: string
  status: string
  action_count: number
}

export interface MeResponse {
  user: User
  primary_team_id: string | null
  teams: Team[]
}

export interface EmailDraft {
  subject: string
  body: string
  mailto: string
}

export interface MeetingCreated {
  meeting_id: string
  status: string
}

export interface Series {
  id: string
  name: string
  team_id: string
  description: string | null
}

export interface SearchResult {
  meeting_id: string
  title: string
  date: string
  status: string
  team_name: string
  snippet: string
}

export interface AuditLogEntry {
  id: string
  action: string
  entity_type: string
  entity_id: string
  actor_id: string | null
  detail: string | null
  created_at: string
}

export interface ActionItemWithContext extends ActionItem {
  team_id: string
  team_name: string
  meeting_title: string
}

export interface DigestItem {
  description: string
  assignee_name: string | null
  due_date: string | null
  priority: string
  overdue: boolean
  team_name: string
  meeting_title: string
}

export interface Digest {
  subject: string
  body: string
  mailto: string
  items: DigestItem[]
}

export interface TeamTreeNode {
  id: string
  name: string
  description: string | null
  children: TeamTreeNode[]
}

export interface TeamRollup {
  team: TeamInfo
  descendant_count: number
  open_action_items: number
  recent_meetings: MeetingSummary[]
}

export interface OutlookInfo {
  subject: string
  body: string
  ics_url: string
  calendar_web_url: string
  email_web_url: string
  server_send_enabled: boolean
}

export interface AdminUser {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  team_count: number
}

export interface AdminTeam {
  id: string
  name: string
  description: string | null
  manager_id: string | null
  parent_team_id: string | null
  member_count: number
}

export interface AdminMember {
  user_id: string
  full_name: string
  email: string
  role: string
}
