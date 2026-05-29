// frontend/src/hooks/useClientHealth.ts
import { useState, useEffect, useCallback } from 'react';
import { useClientStore } from '@/stores/clientStore';
import type { ClientHealthReport } from '@/types';

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? '';

/**
 * Fetches health data for a given client.
 * Stores the result in the global store and returns local loading/error state.
 */
export function useClientHealth(clientName: string | null) {
  const { setClientHealthScore } = useClientStore();
  const [health, setHealth] = useState<ClientHealthReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    if (!clientName) {
      setHealth(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${BASE_URL}/api/clients/${encodeURIComponent(clientName)}/health`,
      );
      if (!res.ok) {
        throw new Error(`Health fetch failed (${res.status})`);
      }
      const data: ClientHealthReport = await res.json();
      setHealth(data);
      setClientHealthScore(clientName, data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('Failed to fetch client health:', message);
    } finally {
      setLoading(false);
    }
  }, [clientName, setClientHealthScore]);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return { health, loading, error, refresh: fetchHealth };
}
