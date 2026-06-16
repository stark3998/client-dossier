// frontend/src/components/search/GlobalSearchBar.tsx
import { useState, useRef, useEffect, useCallback } from 'react';
import { VscSearch, VscLoading } from 'react-icons/vsc';
import { InboxSearchPanel } from './InboxSearchPanel';
import { useInboxSearch } from '@/hooks/useInboxSearch';

/**
 * Global inbox search bar for the app header.
 * Opens InboxSearchPanel on focus or Ctrl+K / Cmd+K.
 * Closes on Escape or clicking the backdrop.
 *
 * Usage:
 *   <GlobalSearchBar />
 */
export function GlobalSearchBar() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const searchState = useInboxSearch();
  const { search, loading, reset } = searchState;

  // Ctrl+K / Cmd+K to open; Escape to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === 'Escape') {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Focus input when panel opens
  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    }
  }, [open]);

  const handleClose = useCallback(() => {
    setOpen(false);
    setQuery('');
    reset();
  }, [reset]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (query.trim()) {
        search(query);
      }
    },
    [query, search],
  );

  return (
    <>
      {/* Search bar — sits in the header */}
      <form onSubmit={handleSubmit} className="flex items-center gap-1.5" role="search">
        <div className="relative flex items-center">
          <VscSearch
            size={12}
            className="absolute left-2.5 text-text-muted pointer-events-none"
            aria-hidden="true"
          />
          <input
            ref={inputRef}
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setOpen(true)}
            placeholder="Search inbox… (Ctrl+K)"
            className="w-56 bg-bg-secondary border border-border-default rounded pl-7 pr-3 py-1 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/50 focus:w-72 transition-all duration-200"
            aria-label="Search Outlook inbox"
          />
          {loading && (
            <VscLoading
              size={11}
              className="absolute right-2.5 text-accent animate-spin"
              aria-hidden="true"
            />
          )}
        </div>
      </form>

      {open && (
        <InboxSearchPanel onClose={handleClose} search={search} results={searchState} />
      )}
    </>
  );
}
