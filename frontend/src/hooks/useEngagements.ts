// src/hooks/useEngagements.ts
import { useState, useEffect, useCallback } from 'react';
import { useClientStore } from '@/stores/clientStore';
import { useApiFetch } from '@/hooks/useApiFetch';
import type { Engagement, Risk } from '@/types';

export function useEngagements() {
  const { activeClient } = useClientStore();
  const [engagements, setEngagements] = useState<Engagement[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(false);
  const { apiFetch } = useApiFetch();

  const fetchEngagements = useCallback(async () => {
    if (!activeClient) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/api/clients/${encodeURIComponent(activeClient)}/engagements`);
      if (res.ok) {
        const data = await res.json();
        setEngagements(data.engagements || []);
      }
    } catch (err) {
      console.error('Failed to fetch engagements:', err);
    } finally {
      setLoading(false);
    }
  }, [activeClient, apiFetch]);

  const fetchRisks = useCallback(async () => {
    if (!activeClient) return;
    try {
      const res = await apiFetch(`/api/clients/${encodeURIComponent(activeClient)}/risks`);
      if (res.ok) {
        const data = await res.json();
        setRisks(data.risks || []);
      }
    } catch (err) {
      console.error('Failed to fetch risks:', err);
    }
  }, [activeClient, apiFetch]);

  useEffect(() => {
    fetchEngagements();
    fetchRisks();
  }, [fetchEngagements, fetchRisks]);

  return { engagements, risks, loading, refresh: fetchEngagements };
}
