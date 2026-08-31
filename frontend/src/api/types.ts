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
  kind: string
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

export interface Tag {
  id: string
  name: string
  type: string
}

export interface MeetingSummary {
  id: string
  title: string
  date: string
  status: string
  team_id: string
  team_name: string
  series_id: string | null
  series_name: string | null
}

export interface MeetingFollowUp {
  id: string
  follow_up_type: string
  title: string
  issue: string | null
  participants: string[] | null
  rationale: string | null
  status: string
  created_at: string
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
  team_id: string
  team_name: string
  series_id: string | null
  series_name: string | null
  meeting_title: string
  tags: Tag[]
  source_excerpt: string | null
  source_speaker: string | null
  source_timestamp: string | null
  confidence: number | null
  attribution_method: string | null
  requester: string | null
  related_participants: string[] | null
  completion_notes: string | null
  completion_links: string | null
  completion_follow_up: string | null
}

export interface DashboardData {
  team_info: TeamInfo
  recent_meetings: MeetingSummary[]
  open_action_items: ActionItem[]
  follow_ups: MeetingFollowUp[]
}

export interface AllDashboardData {
  recent_meetings: MeetingSummary[]
  open_action_items: ActionItem[]
  follow_ups: MeetingFollowUp[]
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
  raw_transcript: string
  source_filename: string | null
  follow_ups: MeetingFollowUp[]
  my_role: string
}

export interface MeetingPermission {
  user_id: string
  full_name: string
  email: string
  role: string
}

export interface MeetingListRow {
  id: string
  title: string
  date: string
  status: string
  action_count: number
  team_id: string
  team_name: string
  series_id: string | null
  series_name: string | null
}

export interface CountByKey {
  key: string
  label: string
  count: number
}

export interface AnalyticsData {
  open_count: number
  overdue_count: number
  by_team: CountByKey[]
  by_theme: CountByKey[]
  by_region: CountByKey[]
  by_assignee: CountByKey[]
  top_themes: CountByKey[]
  follow_up_types: CountByKey[]
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
  kind: string
  meeting_id: string
  title: string
  date: string
  status: string
  team_name: string
  snippet: string
  speaker: string | null
  action_item_id: string | null
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

export interface ActionItemWithContext extends ActionItem {}

export interface ActionItemComment {
  id: string
  action_item_id: string
  author_id: string | null
  author_name: string | null
  body: string
  parent_id: string | null
  created_at: string
}

export interface Notification {
  id: string
  kind: string
  entity_type: string | null
  entity_id: string | null
  meeting_id: string | null
  text: string | null
  read: boolean
  actor_name: string | null
  created_at: string
}

export interface UnreadCount {
  count: number
}

export interface ActionItemHistoryEntry {
  type: 'change' | 'comment'
  field: string | null
  from_value: string | null
  to_value: string | null
  comment: string | null
  actor_name: string | null
  created_at: string
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
  kind: string
  member_count: number
}

export interface AdminMember {
  user_id: string
  full_name: string
  email: string
  role: string
}
