import { useCallback, useEffect, useRef, useState } from 'react';
import { useClientStore } from '@/stores/clientStore';
import { useFileTree } from '@/hooks/useFileTree';
import { useApiFetch } from '@/hooks/useApiFetch';
import type { FileNode } from '@/types';

const SYNC_JOB_KEY = 'sync_active_job_id';
const SYNC_MODE_KEY = 'sync_active_job_mode';

type SyncMode = 'incremental' | 'complete';
type FileStatus = 'idle' | 'indexing' | 'done' | 'error' | 'pending';

export interface FileEvent {
  file_name: string;
  status: 'done' | 'error';
  chunks?: number;
  duration_ms?: number;
  error?: string;
}

interface SyncProgress {
  processed: number;
  total: number;
  skipped: number;
  activeFiles: string[];
  mode: SyncMode;
  fileEvents: FileEvent[];
}

function collectFilePaths(node: FileNode | null): string[] {
  if (!node) return [];
  if (node.type === 'file') return [node.path];
  return (node.children ?? []).flatMap(collectFilePaths);
}

export function useSync() {
  const { activeClient, setLastIndexed, fileTree, setIngestionStatus, setAllIngestionStatuses } = useClientStore();
  const { refresh } = useFileTree();
  const { apiFetch } = useApiFetch();
  const [isSyncing, setIsSyncing] = useState(false);
  const [progress, setProgress] = useState<SyncProgress>({
    processed: 0, total: 0, skipped: 0, activeFiles: [], mode: 'incremental', fileEvents: [],
  });
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevActiveRef = useRef<Set<string>>(new Set());

  const stopPolling = useCallback((withError?: string) => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    localStorage.removeItem(SYNC_JOB_KEY);
    localStorage.removeItem(SYNC_MODE_KEY);
    prevActiveRef.current = new Set();
    setIsSyncing(false);
    if (withError !== undefined) setError(withError);
  }, []);

  const fetchIndexedFiles = useCallback(async (client: string) => {
    try {
      const res = await apiFetch(`/api/ingest/indexed-files?client_name=${encodeURIComponent(client)}`);
      if (!res.ok) return;
      const { files } = await res.json() as { files: { file_path: string }[] };

      const indexedPaths = new Set(files.map((f) => f.file_path));
      const allPaths = collectFilePaths(fileTree);

      const statuses: Record<string, FileStatus> = {};
      for (const path of allPaths) {
        statuses[path] = indexedPaths.has(path) ? 'done' : 'pending';
      }
      setAllIngestionStatuses(statuses);
    } catch {
      // silently ignore — status dots are best-effort
    }
  }, [fileTree, setAllIngestionStatuses, apiFetch]);

  // Refresh indexed status whenever client or file tree changes
  useEffect(() => {
    if (activeClient && fileTree) {
      fetchIndexedFiles(activeClient);
    }
  }, [activeClient, fileTree, fetchIndexedFiles]);

  const startPolling = useCallback((jobId: string, mode: SyncMode) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const poll = await apiFetch(`/api/ingest/${jobId}`);
        if (poll.status === 404) {
          stopPolling();
          return;
        }
        if (!poll.ok) return;

        const job = await poll.json();
        const activeFiles: string[] = job.active_files ?? [];

        // Update per-file status dots: mark newly active as indexing, removed as done
        const prev = prevActiveRef.current;
        const next = new Set(activeFiles);
        for (const f of prev) {
          if (!next.has(f)) setIngestionStatus(f, 'done');
        }
        for (const f of next) {
          if (!prev.has(f)) setIngestionStatus(f, 'indexing');
        }
        prevActiveRef.current = next;

        setProgress({
          processed: job.processed_files ?? 0,
          total: job.total_files ?? 0,
          skipped: job.skipped_files ?? 0,
          activeFiles,
          mode,
          fileEvents: job.file_events ?? [],
        });

        if (job.status === 'done') {
          stopPolling();
          setLastIndexed(new Date().toISOString());
          refresh();
          if (activeClient) fetchIndexedFiles(activeClient);
        } else if (job.status === 'error') {
          stopPolling(job.error ?? 'Sync failed');
        }
      } catch {
        stopPolling('Polling failed');
      }
    }, 2000);
  }, [stopPolling, setLastIndexed, refresh, activeClient, fetchIndexedFiles, setIngestionStatus, apiFetch]);

  // Resume any in-progress sync after page reload
  useEffect(() => {
    const savedJobId = localStorage.getItem(SYNC_JOB_KEY);
    const savedMode = (localStorage.getItem(SYNC_MODE_KEY) ?? 'incremental') as SyncMode;
    if (!savedJobId || pollRef.current) return;
    setIsSyncing(true);
    startPolling(savedJobId, savedMode);
  }, [startPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const sync = useCallback(async (mode: SyncMode = 'incremental') => {
    if (!activeClient || isSyncing) return;
    setIsSyncing(true);
    setError(null);
    setProgress({ processed: 0, total: 0, skipped: 0, activeFiles: [], mode, fileEvents: [] });

    try {
      const res = await apiFetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: activeClient, mode }),
      });

      if (!res.ok) throw new Error(`Failed to start sync: ${res.status}`);

      const { job_id } = await res.json();
      localStorage.setItem(SYNC_JOB_KEY, job_id);
      localStorage.setItem(SYNC_MODE_KEY, mode);
      startPolling(job_id, mode);
    } catch (err) {
      setIsSyncing(false);
      setError(err instanceof Error ? err.message : 'Sync failed');
    }
  }, [activeClient, isSyncing, startPolling, apiFetch]);

  return { sync, isSyncing, progress, error };
}
