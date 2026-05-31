import { useCallback, useEffect, useRef, useState } from 'react';
import { useClientStore } from '@/stores/clientStore';
import { useFileTree } from '@/hooks/useFileTree';

interface SyncProgress {
  processed: number;
  total: number;
  currentFile: string;
}

export function useSync() {
  const { activeClient, setLastIndexed } = useClientStore();
  const { refresh } = useFileTree();
  const [isSyncing, setIsSyncing] = useState(false);
  const [progress, setProgress] = useState<SyncProgress>({ processed: 0, total: 0, currentFile: '' });
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const sync = useCallback(async () => {
    if (!activeClient || isSyncing) return;
    setIsSyncing(true);
    setError(null);
    setProgress({ processed: 0, total: 0, currentFile: '' });

    try {
      const res = await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: activeClient }),
      });

      if (!res.ok) {
        throw new Error(`Failed to start sync: ${res.status}`);
      }

      const { job_id } = await res.json();

      pollRef.current = setInterval(async () => {
        try {
          const poll = await fetch(`/api/ingest/${job_id}`);
          if (!poll.ok) return;

          const job = await poll.json();
          setProgress({
            processed: job.processed_files ?? 0,
            total: job.total_files ?? 0,
            currentFile: job.current_file ?? '',
          });

          if (job.status === 'done') {
            stopPolling();
            setIsSyncing(false);
            setLastIndexed(new Date().toISOString());
            refresh();
          } else if (job.status === 'error') {
            stopPolling();
            setIsSyncing(false);
            setError(job.error ?? 'Sync failed');
          }
        } catch {
          stopPolling();
          setIsSyncing(false);
          setError('Polling failed');
        }
      }, 2000);
    } catch (err) {
      setIsSyncing(false);
      setError(err instanceof Error ? err.message : 'Sync failed');
    }
  }, [activeClient, isSyncing, setLastIndexed, refresh, stopPolling]);

  return { sync, isSyncing, progress, error };
}
