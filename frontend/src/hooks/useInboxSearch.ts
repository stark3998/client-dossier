// frontend/src/hooks/useInboxSearch.ts
import { useState, useCallback } from 'react';
import { useApiFetch } from '@/hooks/useApiFetch';
import type { InboxSearchResponse, InboxSearchResult, ParsedEmailFilters } from '@/types';

interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
}

/**
 * Hook for AI-powered inbox search with conversational refinement.
 * Maintains conversation history so follow-up queries carry context.
 */
export function useInboxSearch() {
  const { apiFetch } = useApiFetch();
  const [results, setResults] = useState<InboxSearchResult[]>([]);
  const [summary, setSummary] = useState('');
  const [expandedQueries, setExpandedQueries] = useState<string[]>([]);
  const [filtersApplied, setFiltersApplied] = useState<ParsedEmailFilters>({});
  const [totalFound, setTotalFound] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const search = useCallback(
    async (query: string, days = 90) => {
      if (!query.trim()) return;
      setLoading(true);
      setError(null);
      try {
        const res = await apiFetch('/api/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query,
            days,
            conversation_history: conversationHistory,
          }),
        });
        if (!res.ok) throw new Error(`Search failed: ${res.status}`);
        const data: InboxSearchResponse = await res.json();
        setResults(data.results);
        setSummary(data.summary);
        setExpandedQueries(data.expanded_queries);
        setFiltersApplied(data.filters_applied);
        setTotalFound(data.total_found);
        setHasSearched(true);
        setConversationHistory((prev) => [
          ...prev,
          { role: 'user', content: query },
          {
            role: 'assistant',
            content: data.summary || `Found ${data.total_found} emails.`,
          },
        ]);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Search failed');
      } finally {
        setLoading(false);
      }
    },
    [apiFetch, conversationHistory],
  );

  const reset = useCallback(() => {
    setResults([]);
    setSummary('');
    setExpandedQueries([]);
    setFiltersApplied({});
    setTotalFound(0);
    setHasSearched(false);
    setError(null);
    setConversationHistory([]);
  }, []);

  return {
    results,
    summary,
    expandedQueries,
    filtersApplied,
    totalFound,
    loading,
    error,
    hasSearched,
    conversationHistory,
    search,
    reset,
  };
}
