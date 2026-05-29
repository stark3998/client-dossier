// frontend/src/hooks/useBriefing.ts
import { useState, useEffect, useCallback } from 'react';
import type { BriefingData } from '@/types';

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? '';
const LAST_VISIT_UPDATE_DELAY_MS = 2000;

function getLastVisitKey(clientName: string): string {
  return `last_visit_${clientName}`;
}

/**
 * Fetches a briefing for the given client based on the time since the last visit.
 * Updates the last-visit timestamp in localStorage after a short delay so the
 * briefing captures the full delta.
 */
export function useBriefing(clientName: string | null) {
  const [briefing, setBriefing] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!clientName) {
      setBriefing(null);
      return;
    }

    const lastVisit = localStorage.getItem(getLastVisitKey(clientName)) ?? '';

    setLoading(true);

    const params = new URLSearchParams();
    if (lastVisit) {
      params.set('since', lastVisit);
    }

    fetch(`${BASE_URL}/api/clients/${encodeURIComponent(clientName)}/briefing?${params.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Briefing fetch failed (${res.status})`);
        return res.json();
      })
      .then((data: BriefingData) => {
        setBriefing(data);

        // Delay the last-visit update so subsequent queries still capture the delta
        setTimeout(() => {
          localStorage.setItem(
            getLastVisitKey(clientName),
            new Date().toISOString(),
          );
        }, LAST_VISIT_UPDATE_DELAY_MS);
      })
      .catch((err) => {
        console.error('Failed to fetch briefing:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [clientName]);

  const dismiss = useCallback(() => {
    setBriefing(null);
  }, []);

  return { briefing, loading, dismiss };
}
