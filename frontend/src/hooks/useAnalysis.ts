// src/hooks/useAnalysis.ts
import { useState, useEffect, useCallback } from 'react';
import { useClientStore } from '@/stores/clientStore';
import type { AnalysisResult } from '@/types';

export function useAnalysis() {
  const { activeClient } = useClientStore();
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchResults = useCallback(async () => {
    if (!activeClient) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/analysis/${encodeURIComponent(activeClient)}`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      }
    } catch (err) {
      console.error('Failed to fetch analysis:', err);
    } finally {
      setLoading(false);
    }
  }, [activeClient]);

  useEffect(() => { fetchResults(); }, [fetchResults]);

  return { results, loading, refresh: fetchResults };
}
