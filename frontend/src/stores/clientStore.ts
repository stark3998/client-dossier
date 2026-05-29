import { create } from 'zustand';
import type {
  FileNode, ChatMessage, ClientMemory, McpServerStatus, SourceChip,
  UploadProgress, Notification, AgentReasoningStep, ClientHealthReport,
} from '@/types';

interface ClientStore {
  // Client
  activeClient: string | null;
  clients: string[];
  setActiveClient: (name: string) => void;

  // Files
  fileTree: FileNode | null;
  selectedFile: string | null;
  expandedFolders: Set<string>;
  setFileTree: (tree: FileNode | null) => void;
  selectFile: (path: string | null) => void;
  toggleFolder: (path: string) => void;
  ingestionStatus: Record<string, 'idle' | 'indexing' | 'done' | 'error'>;
  setIngestionStatus: (path: string, status: 'idle' | 'indexing' | 'done' | 'error') => void;

  // Chat
  messages: ChatMessage[];
  isStreaming: boolean;
  streamBuffer: string;
  streamSources: SourceChip[];
  addMessage: (msg: ChatMessage) => void;
  appendToken: (token: string) => void;
  addStreamSource: (source: SourceChip) => void;
  finalizeStream: () => void;
  startStream: () => void;
  clearMessages: () => void;

  // Insights
  clientMemory: ClientMemory | null;
  setClientMemory: (memory: ClientMemory | null) => void;

  // UI
  leftPanelWidth: number;
  rightPanelWidth: number;
  leftPanelCollapsed: boolean;
  rightPanelCollapsed: boolean;
  setLeftPanelWidth: (w: number) => void;
  setRightPanelWidth: (w: number) => void;
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
  mcpServers: McpServerStatus[];
  setMcpServers: (servers: McpServerStatus[]) => void;
  lastIndexed: string | null;
  setLastIndexed: (ts: string) => void;

  // Sidebar tab
  sidebarTab: 'files' | 'tools';
  setSidebarTab: (tab: 'files' | 'tools') => void;

  // Upload
  uploads: Record<string, UploadProgress>;
  setUpload: (fileId: string, progress: UploadProgress) => void;
  clearUpload: (fileId: string) => void;

  // MCP panel
  showMCPPanel: boolean;
  setShowMCPPanel: (show: boolean) => void;

  // Notifications
  notifications: Notification[];
  unreadCount: number;
  addNotification: (n: Notification) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;

  // Command palette
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;

  // Notification drawer
  notificationDrawerOpen: boolean;
  setNotificationDrawerOpen: (open: boolean) => void;

  // Search & filters
  globalSearchQuery: string;
  setGlobalSearchQuery: (q: string) => void;
  activeFilters: Record<string, string[]>;
  setActiveFilters: (key: string, values: string[]) => void;
  clearFilters: () => void;

  // Client health
  clientHealthScores: Record<string, ClientHealthReport>;
  setClientHealthScore: (name: string, report: ClientHealthReport) => void;

  // Agent reasoning (streaming)
  streamReasoning: AgentReasoningStep[];
  addReasoningStep: (step: AgentReasoningStep) => void;
}

export const useClientStore = create<ClientStore>((set) => ({
  activeClient: null,
  clients: [],
  setActiveClient: (name) => set({ activeClient: name }),

  fileTree: null,
  selectedFile: null,
  expandedFolders: new Set<string>(),
  setFileTree: (tree) => set({ fileTree: tree }),
  selectFile: (path) => set({ selectedFile: path }),
  toggleFolder: (path) =>
    set((state) => {
      const next = new Set(state.expandedFolders);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return { expandedFolders: next };
    }),
  ingestionStatus: {},
  setIngestionStatus: (path, status) =>
    set((state) => ({
      ingestionStatus: { ...state.ingestionStatus, [path]: status },
    })),

  messages: [],
  isStreaming: false,
  streamBuffer: '',
  streamSources: [],
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  appendToken: (token) =>
    set((state) => ({ streamBuffer: state.streamBuffer + token })),
  addStreamSource: (source) =>
    set((state) => ({ streamSources: [...state.streamSources, source] })),
  startStream: () => set({ isStreaming: true, streamBuffer: '', streamSources: [], streamReasoning: [] }),
  finalizeStream: () =>
    set((state) => {
      if (!state.streamBuffer) return { isStreaming: false };
      const msg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: state.streamBuffer,
        sources: state.streamSources,
        timestamp: new Date().toISOString(),
        reasoning: state.streamReasoning.length > 0 ? [...state.streamReasoning] : undefined,
      };
      return {
        messages: [...state.messages, msg],
        isStreaming: false,
        streamBuffer: '',
        streamSources: [],
        streamReasoning: [],
      };
    }),
  clearMessages: () => set({ messages: [] }),

  clientMemory: null,
  setClientMemory: (memory) => set({ clientMemory: memory }),

  leftPanelWidth: 280,
  rightPanelWidth: 320,
  leftPanelCollapsed: false,
  rightPanelCollapsed: false,
  setLeftPanelWidth: (w) => set({ leftPanelWidth: w }),
  setRightPanelWidth: (w) => set({ rightPanelWidth: w }),
  toggleLeftPanel: () => set((s) => ({ leftPanelCollapsed: !s.leftPanelCollapsed })),
  toggleRightPanel: () => set((s) => ({ rightPanelCollapsed: !s.rightPanelCollapsed })),
  mcpServers: [],
  setMcpServers: (servers) => set({ mcpServers: servers }),
  lastIndexed: null,
  setLastIndexed: (ts) => set({ lastIndexed: ts }),

  sidebarTab: 'files',
  setSidebarTab: (tab) => set({ sidebarTab: tab }),

  uploads: {},
  setUpload: (fileId, progress) =>
    set((state) => ({ uploads: { ...state.uploads, [fileId]: progress } })),
  clearUpload: (fileId) =>
    set((state) => {
      const { [fileId]: _, ...rest } = state.uploads;
      return { uploads: rest };
    }),

  showMCPPanel: false,
  setShowMCPPanel: (show) => set({ showMCPPanel: show }),

  // Notifications
  notifications: [],
  unreadCount: 0,
  addNotification: (n) =>
    set((state) => ({
      notifications: [n, ...state.notifications].slice(0, 100),
      unreadCount: state.unreadCount + 1,
    })),
  markNotificationRead: (id) =>
    set((state) => {
      const updated = state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      );
      return {
        notifications: updated,
        unreadCount: updated.filter((n) => !n.read).length,
      };
    }),
  markAllNotificationsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  // Command palette
  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

  // Notification drawer
  notificationDrawerOpen: false,
  setNotificationDrawerOpen: (open) => set({ notificationDrawerOpen: open }),

  // Search & filters
  globalSearchQuery: '',
  setGlobalSearchQuery: (q) => set({ globalSearchQuery: q }),
  activeFilters: {},
  setActiveFilters: (key, values) =>
    set((state) => ({
      activeFilters: { ...state.activeFilters, [key]: values },
    })),
  clearFilters: () => set({ activeFilters: {} }),

  // Client health
  clientHealthScores: {},
  setClientHealthScore: (name, report) =>
    set((state) => ({
      clientHealthScores: { ...state.clientHealthScores, [name]: report },
    })),

  // Agent reasoning
  streamReasoning: [],
  addReasoningStep: (step) =>
    set((state) => ({ streamReasoning: [...state.streamReasoning, step] })),
}));
