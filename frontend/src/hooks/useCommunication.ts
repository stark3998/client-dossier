// frontend/src/hooks/useCommunication.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  CommSummary,
  CommunicationConfig,
  DraftReply,
  EmailThread,
  MeetingLog,
  ScannedEmail,
  SourceChip,
} from '../types';

const API = import.meta.env.VITE_BACKEND_URL ?? '';

function apiUrl(path: string) {
  return `${API}${path}`;
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// -- Emails -------------------------------------------------------------------

export function useEmails(clientName: string, days = 7) {
  const [emails, setEmails] = useState<ScannedEmail[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (search?: string, folder?: string) => {
      if (!clientName) return;
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ days: String(days) });
        if (search) params.set('search', search);
        if (folder) params.set('folder', folder);
        const data = await fetchJSON<{ emails: ScannedEmail[] }>(
          apiUrl(`/api/communication/${encodeURIComponent(clientName)}/emails?${params}`)
        );
        setEmails(data.emails);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [clientName, days]
  );

  useEffect(() => { load(); }, [load]);

  return { emails, loading, error, reload: load };
}

export async function fetchEmail(clientName: string, emailId: string): Promise<ScannedEmail> {
  return fetchJSON<ScannedEmail>(
    apiUrl(`/api/communication/${encodeURIComponent(clientName)}/emails/${emailId}`)
  );
}

// -- Meetings -----------------------------------------------------------------

export function useMeetings(clientName: string, days = 30) {
  const [meetings, setMeetings] = useState<MeetingLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!clientName) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJSON<{ meetings: MeetingLog[] }>(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/meetings?days=${days}`)
      );
      setMeetings(data.meetings);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [clientName, days]);

  useEffect(() => { load(); }, [load]);

  return { meetings, loading, error, reload: load };
}

export async function fetchTranscript(clientName: string, meetingId: string): Promise<void> {
  await fetchJSON(
    apiUrl(`/api/communication/${encodeURIComponent(clientName)}/meetings/${meetingId}/fetch-transcript`),
    { method: 'POST' }
  );
}

// -- Drafts -------------------------------------------------------------------

export function useDrafts(clientName: string, status?: string) {
  const [drafts, setDrafts] = useState<DraftReply[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!clientName) return;
    setLoading(true);
    setError(null);
    try {
      const params = status ? `?status=${status}` : '';
      const data = await fetchJSON<{ drafts: DraftReply[] }>(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/drafts${params}`)
      );
      setDrafts(data.drafts);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [clientName, status]);

  useEffect(() => { load(); }, [load]);

  const updateDraft = useCallback(
    async (draftId: string, updates: Partial<Pick<DraftReply, 'subject' | 'body' | 'to' | 'cc'>>) => {
      await fetchJSON(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/drafts/${draftId}`),
        { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updates) }
      );
      await load();
    },
    [clientName, load]
  );

  const approveDraft = useCallback(
    async (draftId: string) => {
      await fetchJSON(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/drafts/${draftId}/approve`),
        { method: 'POST' }
      );
      await load();
    },
    [clientName, load]
  );

  const submitFeedback = useCallback(
    async (draftId: string, feedback: string) => {
      await fetchJSON(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/drafts/${draftId}/feedback`),
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ feedback }) }
      );
    },
    [clientName]
  );

  const discardDraft = useCallback(
    async (draftId: string) => {
      await fetchJSON(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/drafts/${draftId}`),
        { method: 'DELETE' }
      );
      await load();
    },
    [clientName, load]
  );

  return { drafts, loading, error, reload: load, updateDraft, approveDraft, submitFeedback, discardDraft };
}

// -- Config -------------------------------------------------------------------

export function useCommConfig(clientName: string) {
  const [config, setConfig] = useState<CommunicationConfig | null>(null);
  const [accounts, setAccounts] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!clientName) return;
    setLoading(true);
    try {
      const [configData, accountData] = await Promise.all([
        fetchJSON<{ config: CommunicationConfig | null }>(
          apiUrl(`/api/communication/${encodeURIComponent(clientName)}/config`)
        ),
        fetchJSON<{ accounts: string[] }>(
          apiUrl(`/api/communication/${encodeURIComponent(clientName)}/accounts`)
        ),
      ]);
      setConfig(configData.config);
      setAccounts(accountData.accounts);
    } finally {
      setLoading(false);
    }
  }, [clientName]);

  useEffect(() => { load(); }, [load]);

  const saveConfig = useCallback(
    async (cfg: CommunicationConfig) => {
      const saved = await fetchJSON<CommunicationConfig>(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/config`),
        { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg) }
      );
      setConfig(saved);
    },
    [clientName]
  );

  const fetchFolders = useCallback(
    async (accountName: string): Promise<string[]> => {
      const data = await fetchJSON<{ folders: string[] }>(
        apiUrl(
          `/api/communication/${encodeURIComponent(clientName)}/accounts/${encodeURIComponent(accountName)}/folders`
        )
      );
      return data.folders;
    },
    [clientName]
  );

  return { config, accounts, loading, reload: load, saveConfig, fetchFolders };
}

// -- Scan trigger -------------------------------------------------------------

export async function triggerScan(clientName: string): Promise<void> {
  await fetchJSON(
    apiUrl(`/api/communication/${encodeURIComponent(clientName)}/scan`),
    { method: 'POST' }
  );
}

// -- Summary ------------------------------------------------------------------

// -- Threads ------------------------------------------------------------------

export function useThreads(clientName: string, days = 14) {
  const [threads, setThreads] = useState<EmailThread[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (search?: string) => {
      if (!clientName) return;
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ days: String(days) });
        if (search) params.set('search', search);
        const data = await fetchJSON<{ threads: EmailThread[] }>(
          apiUrl(`/api/communication/${encodeURIComponent(clientName)}/threads?${params}`)
        );
        setThreads(data.threads);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [clientName, days]
  );

  useEffect(() => { load(); }, [load]);
  return { threads, loading, error, reload: load };
}

export function useThread(clientName: string, threadKey: string | null) {
  const [emails, setEmails] = useState<ScannedEmail[]>([]);
  const [subject, setSubject] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!clientName || !threadKey) { setEmails([]); return; }
    setLoading(true);
    fetchJSON<{ emails: ScannedEmail[]; subject: string }>(
      apiUrl(`/api/communication/${encodeURIComponent(clientName)}/threads/${encodeURIComponent(threadKey)}`)
    )
      .then((d) => { setEmails(d.emails); setSubject(d.subject); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [clientName, threadKey]);

  return { emails, subject, loading };
}

export function useThreadInsight(clientName: string, threadKey: string | null) {
  const [content, setContent] = useState('');
  const [sources, setSources] = useState<SourceChip[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [cached, setCached] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Reset when thread changes
  useEffect(() => {
    setContent('');
    setSources([]);
    setCached(false);
    wsRef.current?.close();
    wsRef.current = null;
  }, [threadKey]);

  const analyze = useCallback(() => {
    if (!clientName || !threadKey || isStreaming) return;
    wsRef.current?.close();

    setContent('');
    setSources([]);
    setIsStreaming(true);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/communication/${encodeURIComponent(clientName)}/threads/${encodeURIComponent(threadKey)}/insight`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data as string);
      if (msg.type === 'token' && msg.content) {
        setContent((prev) => prev + (msg.content as string));
      } else if (msg.type === 'source' && msg.source) {
        setSources((prev) => {
          const src = msg.source as SourceChip;
          if (prev.some((s) => s.file_path === src.file_path)) return prev;
          return [...prev, src];
        });
      } else if (msg.type === 'done') {
        setIsStreaming(false);
        setCached(true);
        ws.close();
      } else if (msg.type === 'error') {
        setIsStreaming(false);
        ws.close();
      }
    };

    ws.onerror = () => setIsStreaming(false);
    ws.onclose = () => setIsStreaming(false);
  }, [clientName, threadKey, isStreaming]);

  return { content, sources, isStreaming, cached, analyze };
}

export async function fetchCommSummary(clientName: string): Promise<CommSummary> {
  // Uses the agent plugin endpoint indirectly via a dedicated summary query
  // Falling back to deriving from list endpoints if needed
  try {
    const [emailsData, meetingsData, draftsData] = await Promise.all([
      fetchJSON<{ emails: unknown[]; count: number }>(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/emails?days=7`)
      ),
      fetchJSON<{ meetings: unknown[]; count: number }>(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/meetings?upcoming_only=true`)
      ),
      fetchJSON<{ drafts: unknown[]; count: number }>(
        apiUrl(`/api/communication/${encodeURIComponent(clientName)}/drafts?status=pending_review`)
      ),
    ]);
    return {
      emails_last_7d: emailsData.count,
      upcoming_meetings: meetingsData.count,
      pending_drafts: draftsData.count,
    };
  } catch {
    return { emails_last_7d: 0, upcoming_meetings: 0, pending_drafts: 0 };
  }
}
