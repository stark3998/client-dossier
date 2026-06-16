// frontend/src/components/search/InboxSearchPanel.tsx
import { useState, useRef } from 'react';
import { VscClose, VscSparkle, VscLoading, VscChevronDown } from 'react-icons/vsc';
import { SearchResultCard } from './SearchResultCard';
import type { useInboxSearch } from '@/hooks/useInboxSearch';

interface Props {
  onClose: () => void;
  search: (query: string, days?: number) => Promise<void>;
  results: ReturnType<typeof useInboxSearch>;
}

function FilterPill({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-accent/15 text-accent">
      {label}
      <button
        type="button"
        onClick={onRemove}
        className="hover:text-text-primary"
        aria-label={`Remove filter ${label}`}
      >
        <VscClose size={10} />
      </button>
    </span>
  );
}

export function InboxSearchPanel({ onClose, search, results }: Props) {
  const {
    results: emails,
    summary,
    expandedQueries,
    filtersApplied,
    totalFound,
    loading,
    error,
    hasSearched,
  } = results;
  const [refineQuery, setRefineQuery] = useState('');
  const [showExpanded, setShowExpanded] = useState(false);
  const refineRef = useRef<HTMLInputElement>(null);

  const activeFilters = Object.entries(filtersApplied).filter(
    ([, v]) => v !== null && v !== undefined,
  );

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col"
      style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Inbox search"
    >
      <div
        className="bg-bg-panel w-full max-w-2xl mx-auto mt-16 mb-8 rounded-lg border border-border-default flex flex-col max-h-[75vh] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Panel header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-default shrink-0">
          <div className="flex items-center gap-2">
            <VscSparkle size={13} className="text-accent" aria-hidden="true" />
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Inbox Search
            </span>
            {totalFound > 0 && (
              <span className="text-[10px] text-text-muted">— {totalFound} results</span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-muted hover:text-text-primary transition-colors"
            aria-label="Close search"
          >
            <VscClose size={14} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
          {loading && (
            <div className="flex items-center justify-center gap-2 py-8 text-text-muted">
              <VscLoading size={16} className="animate-spin" aria-hidden="true" />
              <span className="text-sm">Searching your inbox…</span>
            </div>
          )}

          {error && !loading && (
            <p className="text-xs text-red-400 text-center py-4" role="alert">
              {error}
            </p>
          )}

          {!loading && hasSearched && (
            <>
              {/* AI Summary */}
              {summary && (
                <div className="rounded-md border border-accent/30 bg-accent/5 p-3 space-y-1">
                  <div className="flex items-center gap-1.5">
                    <VscSparkle size={11} className="text-accent" aria-hidden="true" />
                    <span className="text-[10px] font-semibold text-accent uppercase tracking-wider">
                      AI Summary
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed italic">{summary}</p>
                </div>
              )}

              {/* Active filters */}
              {activeFilters.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {activeFilters.map(([key, val]) => (
                    <FilterPill
                      key={key}
                      label={`${key.replace(/_/g, ' ')}: ${String(val)}`}
                      onRemove={() => {}}
                    />
                  ))}
                </div>
              )}

              {/* Expanded queries toggle */}
              {expandedQueries.length > 1 && (
                <div>
                  <button
                    type="button"
                    onClick={() => setShowExpanded((x) => !x)}
                    className="flex items-center gap-1 text-[10px] text-text-muted hover:text-text-secondary transition-colors"
                    aria-expanded={showExpanded}
                  >
                    <VscChevronDown
                      size={10}
                      className={`transition-transform duration-150 ${showExpanded ? '' : '-rotate-90'}`}
                      aria-hidden="true"
                    />
                    Searched with {expandedQueries.length} query variants
                  </button>
                  {showExpanded && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {expandedQueries.map((q, i) => (
                        <span
                          key={i}
                          className="text-[9px] px-1.5 py-0.5 rounded bg-bg-secondary text-text-muted border border-border-default"
                        >
                          {q}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Results */}
              {emails.length === 0 ? (
                <p className="text-xs text-text-muted text-center py-6">
                  No emails found. Try different keywords or extend the date range.
                </p>
              ) : (
                <div className="space-y-2">
                  {emails.map((r) => (
                    <SearchResultCard key={r.id} result={r} />
                  ))}
                </div>
              )}
            </>
          )}

          {!loading && !hasSearched && (
            <p className="text-xs text-text-muted text-center py-8">
              Type a query above to search your entire Outlook inbox with AI-powered expansion.
            </p>
          )}
        </div>

        {/* Conversation refine input */}
        {hasSearched && (
          <div className="px-4 py-3 border-t border-border-default shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (refineQuery.trim()) {
                  search(refineQuery);
                  setRefineQuery('');
                }
              }}
              className="flex items-center gap-2"
            >
              <input
                ref={refineRef}
                value={refineQuery}
                onChange={(e) => setRefineQuery(e.target.value)}
                placeholder="Refine your search… e.g. 'only from last month' or 'filter to external senders'"
                className="flex-1 bg-bg-secondary border border-border-default rounded px-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 transition-colors"
                aria-label="Refine search query"
              />
              <button
                type="submit"
                disabled={!refineQuery.trim()}
                className="px-3 py-1.5 text-xs bg-accent/20 text-accent rounded hover:bg-accent/30 transition-colors disabled:opacity-40"
              >
                Refine
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
