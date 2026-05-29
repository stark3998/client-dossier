// src/hooks/useTimeline.ts
import { useState, useEffect, useCallback } from 'react';
import { useClientStore } from '@/stores/clientStore';
import type { TimelineEvent } from '@/types';

export function useTimeline() {
  const { activeClient } = useClientStore();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTimeline = useCallback(async () => {
    if (!activeClient) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/clients/${encodeURIComponent(activeClient)}/timeline`);
      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
      }
    } catch (err) {
      console.error('Failed to fetch timeline:', err);
    } finally {
      setLoading(false);
    }
  }, [activeClient]);

  useEffect(() => { fetchTimeline(); }, [fetchTimeline]);

  return { events, loading, refresh: fetchTimeline };
}
