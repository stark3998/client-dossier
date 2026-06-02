// frontend/src/hooks/useInsights.ts
import { useEffect, useState } from 'react';
import { useClientStore } from '@/stores/clientStore';
import { useApiFetch } from '@/hooks/useApiFetch';
import type { ClientMemory } from '@/types';

export function useInsights() {
  const { activeClient, clientMemory, setClientMemory } = useClientStore();
  const [isLoading, setIsLoading] = useState(false);
  const { apiFetch } = useApiFetch();

  useEffect(() => {
    if (!activeClient) {
      setClientMemory(null);
      return;
    }

    setIsLoading(true);
    apiFetch(`/api/insights?client_name=${encodeURIComponent(activeClient)}`)
      .then((res) => res.json())
      .then((data: ClientMemory) => setClientMemory(data))
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [activeClient, setClientMemory, apiFetch]);

  const updateMemory = async (updates: Partial<ClientMemory>) => {
    if (!activeClient) return;
    try {
      const res = await apiFetch(`/api/memory/${encodeURIComponent(activeClient)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const updated = await res.json();
        setClientMemory(updated);
      }
    } catch (err) {
      console.error('Failed to update memory:', err);
    }
  };

  return { memory: clientMemory, isLoading, updateMemory };
}
