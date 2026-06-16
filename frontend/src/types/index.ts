export interface FileNode {
  name: string;
  type: 'folder' | 'file';
  path: string;
  size?: number;
  lastModified?: number;
  children?: FileNode[];
}

export interface SourceChip {
  file_path: string;
  section_title?: string;
  page_number?: number;
  excerpt: string;
  score: number;
}

export interface AgentReasoningStep {
  type: 'thought' | 'plan' | 'tool_call' | 'tool_result' | 'plan_step';
  content: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_source?: string; // "mcp" for MCP plugin calls
  step_number?: number;
  step_total?: number;
  plan_steps?: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources: SourceChip[];
  timestamp: string;
  isStreaming?: boolean;
  reasoning?: AgentReasoningStep[];
}

export interface Stakeholder {
  name: string;
  title?: string;
  email?: string;
}

export interface Deliverable {
  title: string;
  date?: string;
  file_path?: string;
}

export interface ActionItem {
  description: string;
  owner?: string;
  due_date?: string;
  completed: boolean;
}

export interface EngagementDefaults {
  default_phase?: string;
  default_type?: string;
  billing_code?: string;
}

export interface ClientMemory {
  id: string;
  client_name: string;
  industry?: string;
  key_stakeholders: Stakeholder[];
  active_engagements: string[];
  financials_summary?: string;
  pain_points: string[];
  strategic_priorities: string[];
  past_deliverables: Deliverable[];
  open_action_items: ActionItem[];
  engagement_defaults?: EngagementDefaults;
  last_updated?: string;
  sources: string[];
}

export interface McpServerStatus {
  name: string;
  enabled: boolean;
  connected: boolean;
}

export interface IngestStatus {
  job_id: string;
  status: 'pending' | 'running' | 'done' | 'error';
  progress: number;
  current_file?: string;
}

export interface WSMessage {
  type: 'token' | 'source' | 'done' | 'error' | 'thought' | 'plan' | 'plan_step' | 'tool_call' | 'tool_result';
  content?: string;
  source?: SourceChip;
  message?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_source?: string;
  step_number?: number;
  step_total?: number;
  plan_steps?: string[];
}

// ── Engagements & Project Tracking ──────────────────────────────

export interface Engagement {
  id: string;
  name: string;
  client_name: string;
  phase: 'discovery' | 'design' | 'execute' | 'deliver' | 'sustain';
  status: 'active' | 'completed' | 'on-hold' | 'cancelled';
  description: string;
  start_date?: string;
  end_date?: string;
  budget?: number;
  team: string[];
  created_at: string;
  updated_at: string;
}

export interface StatusUpdate {
  id: string;
  engagement_id: string;
  date: string;
  author: string;
  summary: string;
  sentiment: 'positive' | 'neutral' | 'negative' | 'concerning';
  source_file?: string;
}

export interface EnhancedDeliverable {
  id: string;
  title: string;
  type: 'document' | 'presentation' | 'report' | 'code' | 'other';
  engagement_id: string;
  status: 'draft' | 'review' | 'delivered' | 'accepted';
  due_date?: string;
  owner: string;
  feedback?: string;
  file_path?: string;
}

export interface Risk {
  id: string;
  description: string;
  probability: number;
  impact: number;
  mitigation: string;
  status: 'open' | 'mitigating' | 'resolved' | 'accepted';
  engagement_id: string;
  owner: string;
  category: 'technical' | 'commercial' | 'operational' | 'timeline';
}

export interface Interaction {
  id: string;
  type: 'meeting' | 'call' | 'email' | 'workshop';
  date: string;
  participants: string[];
  summary: string;
  action_items: string[];
  source_file?: string;
  engagement_id?: string;
}

// ── Analysis ────────────────────────────────────────────────────

export interface ExtractedStakeholder {
  name: string;
  title?: string;
  email?: string;
  organization?: string;
  confidence: number;
}

export interface ExtractedActionItem {
  description: string;
  owner?: string;
  due_date?: string;
  priority?: string;
}

export interface ExtractedRisk {
  description: string;
  severity?: string;
  category?: string;
}

export interface AnalysisResult {
  id: string;
  file_path: string;
  client_name: string;
  doc_type: string;
  extracted_stakeholders: ExtractedStakeholder[];
  extracted_actions: ExtractedActionItem[];
  extracted_risks: ExtractedRisk[];
  engagement_references: string[];
  key_topics: string[];
  analysis_summary: string;
  analyzed_at: string;
}

// ── File Upload ─────────────────────────────────────────────────

export interface UploadProgress {
  fileId: string;
  fileName: string;
  percent: number;
  status: 'uploading' | 'analyzing' | 'done' | 'error';
  error?: string;
  analysisResult?: AnalysisResult;
}

// ── MCP Servers ─────────────────────────────────────────────────

export interface MCPServerConfig {
  id: string;
  name: string;
  endpoint: string;
  description: string;
  auth_type: string;
  capabilities: string[];
  protocol?: string;
  enabled: boolean;
  builtin?: boolean;
  tool_count?: number;
  status: string;
  last_error?: string;
}

export interface MCPTool {
  name: string;
  description: string;
  category: string;
  inputSchema: {
    type: string;
    properties: Record<string, { type: string; description?: string; default?: unknown; enum?: string[] }>;
    required?: string[];
  };
}

// ── Tools/Skills ────────────────────────────────────────────────

export interface ToolParameter {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: string;
}

export interface Tool {
  plugin: string;
  name: string;
  description: string;
  is_custom: boolean;
  custom_tool_id?: string;
  parameters: ToolParameter[];
}

export interface ToolInvocationResult {
  result: string;
  plugin: string;
  function: string;
}

export interface TimelineEvent {
  type: 'interaction' | 'status_update' | 'analysis';
  subtype: string;
  date: string;
  summary: string;
  id: string;
  source: string;
  participants?: string[];
  author?: string;
  file_path?: string;
}

// ── Notifications ──────────────────────────────────────────────

export interface Notification {
  id: string;
  type: 'analysis_complete' | 'overdue_alert' | 'risk_escalation' | 'memory_updated' | 'engagement_phase_change';
  title: string;
  description: string;
  timestamp: string;
  read: boolean;
  client_name?: string;
  target_route?: string;
  priority: 'low' | 'medium' | 'high';
}

export interface ClientEvent {
  id: string;
  client_name: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  summary: string;
  severity: 'info' | 'warning' | 'critical';
  metadata: Record<string, unknown>;
  created_at: string;
}

// ── Health Scoring ─────────────────────────────────────────────

export interface EngagementHealth {
  score: number;
  deliverables_on_track: number;
  deliverables_overdue: number;
  deliverables_total: number;
  action_items_overdue: number;
  phase_distribution: Record<string, number>;
}

export interface RiskPosture {
  score: number;
  total_risks: number;
  open_risks: number;
  critical_risks: number;
  weighted_severity: number;
  trend: 'improving' | 'stable' | 'worsening';
}

export interface RelationshipHealth {
  score: number;
  days_since_last_interaction: number;
  stakeholders_with_gaps: number;
  total_stakeholders: number;
}

export interface ClientHealthReport {
  client_name: string;
  overall_score: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  engagement_health: EngagementHealth;
  risk_posture: RiskPosture;
  relationship_health: RelationshipHealth;
  computed_at: string;
  alerts: string[];
}

// ── Briefing ───────────────────────────────────────────────────

export interface BriefingData {
  client_name: string;
  since: string;
  new_analyses: { file_path: string; doc_type: string; summary: string }[];
  overdue_items: { description: string; owner: string; due_date: string }[];
  risk_changes: { description: string; severity: string; status: string }[];
  engagement_updates: { name: string; phase: string; change: string }[];
  alert_count: number;
}

// ── Command Palette ────────────────────────────────────────────

export interface CommandPaletteItem {
  id: string;
  type: 'client' | 'engagement' | 'risk' | 'document' | 'stakeholder' | 'action' | 'agent_command';
  label: string;
  description?: string;
  icon?: string;
  action: () => void;
}

// ── Communication ──────────────────────────────────────────────

export interface OutlookAccount {
  display_name: string;
  folders: string[];
}

export interface CommunicationConfig {
  id: string;
  client_name: string;
  domains: string[];
  keywords: string[];
  accounts: OutlookAccount[];
  contacts: string[];
  scan_sent: boolean;
  auto_draft: boolean;
  scan_interval_minutes: number;
  lookback_days: number;
  updated_at?: string;
}

export interface EmailClassification {
  match_type: 'domain_match' | 'contact_match' | 'keyword_match';
  match_field: 'sender' | 'recipient' | 'subject' | 'body' | 'subject_and_body' | 'attendee' | 'unknown';
  matched_value: string;
  keyword_occurrences?: number;
  first_occurrence_position?: number;
}

export interface ScannedEmail {
  id: string;
  client_name: string;
  message_id: string;
  subject: string;
  sender: string;
  recipients: string[];
  body_preview: string;
  body_full?: string;
  received_at: string;
  folder: string;
  account: string;
  thread_id?: string;
  has_draft_reply: boolean;
  draft_reply_id?: string;
  attribution_reason: 'domain_match' | 'keyword_match' | 'contact_match';
  classification?: EmailClassification;
  has_attachment: boolean;
  attachment_names: string[];
  indexed_at: string;
}

export interface MeetingAttendee {
  name: string;
  email: string;
  response_status: 'accepted' | 'declined' | 'tentative' | 'none';
}

export interface MeetingClassification {
  match_type: 'domain_match' | 'contact_match' | 'keyword_match';
  match_field: 'attendee' | 'subject' | 'body' | 'subject_and_body';
  matched_value: string;
}

export interface MeetingLog {
  id: string;
  client_name: string;
  subject: string;
  organizer: string;
  attendees: MeetingAttendee[];
  start_time: string;
  end_time: string;
  location: string;
  agenda: string;
  is_teams_meeting: boolean;
  teams_join_url?: string;
  online_meeting_id?: string;
  global_id?: string;
  my_response: 'accepted' | 'declined' | 'tentative' | 'none';
  transcript_summary?: string;
  action_items_extracted: string[];
  classification?: MeetingClassification;
  indexed_at: string;
}

export interface DraftReply {
  id: string;
  client_name: string;
  email_id: string;
  subject: string;
  to: string[];
  cc: string[];
  body: string;
  status: 'pending_review' | 'edited' | 'pushed_to_outlook' | 'discarded';
  feedback?: string;
  created_at: string;
  pushed_at?: string;
  outlook_entry_id?: string;
}

export interface CommSummary {
  emails_last_7d: number;
  upcoming_meetings: number;
  pending_drafts: number;
}

export interface EmailThread {
  thread_key: string;
  subject: string;
  participants: string[];
  latest_date: string;
  latest_sender: string;
  message_count: number;
  has_draft_reply: boolean;
  has_attachment: boolean;
  attribution_reason: 'domain_match' | 'keyword_match' | 'contact_match';
  classification?: EmailClassification;
  ai_summary?: string;
}

export interface ParsedEmailFilters {
  sender_name?: string | null;
  sender_domain?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  folder?: string | null;
  has_attachment?: boolean | null;
}

export interface InboxSearchResult {
  id: string;
  subject: string;
  sender: string;
  sender_name: string;
  recipients: string[];
  body_preview: string;
  received_at: string | null;
  folder: string;
  account: string;
  has_attachment: boolean;
  attachment_names: string[];
  client_name: string | null;
  client_path: string | null;
  relevance_score: number;
}

export interface InboxSearchResponse {
  results: InboxSearchResult[];
  summary: string;
  expanded_queries: string[];
  filters_applied: ParsedEmailFilters;
  total_found: number;
}
