// frontend/src/components/command/CommandPalette.tsx
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { VscSearch, VscAdd, VscRocket, VscFileSymlinkFile, VscNote, VscTerminal } from 'react-icons/vsc';
import { useClientStore } from '@/stores/clientStore';
import { fuzzyMatch } from '@/utils/fuzzyMatch';

interface PaletteItem {
  id: string;
  section: 'Quick Actions' | 'Agent Commands' | 'Recent';
  label: string;
  description: string;
  icon: React.ReactNode;
}

const ALL_ITEMS: PaletteItem[] = [
  // Quick Actions
  { id: 'new-engagement', section: 'Quick Actions', label: 'New Engagement', description: 'Create a new engagement for this client', icon: <VscAdd size={14} /> },
  { id: 'upload-file', section: 'Quick Actions', label: 'Upload File', description: 'Upload and analyze a document', icon: <VscFileSymlinkFile size={14} /> },
  { id: 'log-interaction', section: 'Quick Actions', label: 'Log Interaction', description: 'Record a meeting, call, or email', icon: <VscNote size={14} /> },
  // Agent Commands
  { id: 'cmd-summarize', section: 'Agent Commands', label: '/summarize this week', description: 'AI summary of the past week', icon: <VscRocket size={14} /> },
  { id: 'cmd-status', section: 'Agent Commands', label: '/draft status report', description: 'Generate a client status report', icon: <VscTerminal size={14} /> },
  { id: 'cmd-overdue', section: 'Agent Commands', label: '/find overdue items', description: 'List all overdue action items and deliverables', icon: <VscSearch size={14} /> },
  { id: 'cmd-compare', section: 'Agent Commands', label: '/compare engagements', description: 'Side-by-side engagement comparison', icon: <VscTerminal size={14} /> },
];

const SECTIONS = ['Quick Actions', 'Agent Commands', 'Recent'] as const;

/**
 * Global command palette overlay triggered by Cmd+K / Ctrl+K.
 * Reads open/close state from useClientStore.
 */
export function CommandPalette() {
  const open = useClientStore((s) => s.commandPaletteOpen);
  const setOpen = useClientStore((s) => s.setCommandPaletteOpen);

  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Global keyboard shortcut
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(!open);
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, setOpen]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      // Delay to let the DOM render
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const filtered = useMemo(() => {
    if (!query.trim()) return ALL_ITEMS;
    return ALL_ITEMS
      .map((item) => ({ item, score: fuzzyMatch(query, item.label).score }))
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .map((r) => r.item);
  }, [query]);

  const selectItem = useCallback((item: PaletteItem) => {
    setOpen(false);
    // Integration with chat/actions comes later — just close for now
    void item;
  }, [setOpen]);

  // Keyboard navigation inside the palette
  const onInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setOpen(false);
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    }
    if (e.key === 'Enter' && filtered[selectedIndex]) {
      selectItem(filtered[selectedIndex]);
    }
  };

  // Scroll selected item into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${selectedIndex}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  if (!open) return null;

  // Group filtered items by section, preserving order
  const grouped = SECTIONS
    .map((section) => ({
      section,
      items: filtered.filter((i) => i.section === section),
    }))
    .filter((g) => g.items.length > 0);

  let flatIndex = -1;

  return (
    // Overlay
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/60 animate-fade-in"
      onClick={() => setOpen(false)}
      role="presentation"
    >
      {/* Modal */}
      <div
        className="w-full max-w-xl bg-bg-secondary border border-border-default rounded-md shadow-2xl animate-slide-in overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        {/* Search input */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border-default">
          <VscSearch size={14} className="text-text-muted shrink-0" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={onInputKeyDown}
            placeholder="Type a command or search..."
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted font-mono focus:outline-none"
            aria-label="Command search"
          />
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-text-muted border border-border-default rounded">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div ref={listRef} className="max-h-72 overflow-y-auto py-1" role="listbox">
          {filtered.length === 0 && (
            <div className="px-4 py-6 text-sm text-text-muted text-center">
              No results for &ldquo;{query}&rdquo;
            </div>
          )}

          {grouped.map((group) => (
            <div key={group.section}>
              <div className="px-4 pt-2 pb-1 text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                {group.section}
              </div>
              {group.items.map((item) => {
                flatIndex++;
                const idx = flatIndex;
                const isSelected = idx === selectedIndex;
                return (
                  <button
                    key={item.id}
                    type="button"
                    data-index={idx}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => selectItem(item)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={`w-full flex items-center gap-3 px-4 py-2 text-left transition-colors ${
                      isSelected ? 'bg-bg-hover' : ''
                    }`}
                  >
                    <span className="text-text-muted shrink-0" aria-hidden="true">{item.icon}</span>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-text-primary truncate">{item.label}</div>
                      <div className="text-[11px] text-text-muted truncate">{item.description}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Footer hint */}
        <div className="flex items-center gap-3 px-4 py-2 border-t border-border-default text-[10px] text-text-muted">
          <span><kbd className="font-mono">↑↓</kbd> navigate</span>
          <span><kbd className="font-mono">↵</kbd> select</span>
          <span><kbd className="font-mono">esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
