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

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources: SourceChip[];
  timestamp: string;
  isStreaming?: boolean;
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
  type: 'token' | 'source' | 'done' | 'error';
  content?: string;
  source?: SourceChip;
  message?: string;
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
  enabled: boolean;
  status: string;
  last_error?: string;
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
