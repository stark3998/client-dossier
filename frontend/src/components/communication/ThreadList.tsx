// frontend/src/components/communication/ThreadList.tsx
import { useState } from 'react';
import { VscAttach, VscMail, VscSearch } from 'react-icons/vsc';
import type { EmailClassification, EmailThread } from '../../types';

interface Props {
  threads: EmailThread[];
  loading: boolean;
  selectedKey: string | null;
  onSelect: (thread: EmailThread) => void;
  onSearch: (q: string) => void;
}

const attributionColors: Record<string, string> = {
  domain_match: 'bg-accent/15 text-accent',
  keyword_match: 'bg-yellow-500/15 text-yellow-400',
  contact_match: 'bg-purple-500/15 text-purple-400',
};

function classificationLabel(cls: EmailClassification | undefined, fallback: string): string {
  if (!cls || !cls.matched_value) return fallback.replace(/_/g, ' ');
  const val = cls.matched_value;
  switch (cls.match_type) {
    case 'domain_match':
      return cls.match_field === 'sender' ? `from @${val}` : `to @${val}`;
    case 'contact_match':
      return cls.match_field === 'sender' ? `from ${val.split('@')[0]}` : `to ${val.split('@')[0]}`;
    case 'keyword_match': {
      const fieldLabel = cls.match_field === 'subject' ? 'subject' : cls.match_field === 'body' ? 'body' : 'subject+body';
      const count = cls.keyword_occurrences && cls.keyword_occurrences > 1 ? ` ×${cls.keyword_occurrences}` : '';
      return `${val} in ${fieldLabel}${count}`;
    }
    default:
      return fallback.replace(/_/g, ' ');
  }
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d`;
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function initials(email: string): string {
  const name = email.split('@')[0].replace(/[._]/g, ' ');
  const parts = name.split(' ').filter(Boolean);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

export function ThreadList({ threads, loading, selectedKey, onSelect, onSearch }: Props) {
  const [query, setQuery] = useState('');

  function handleSearch(q: string) {
    setQuery(q);
    onSearch(q);
  }

  return (
    <div className="flex flex-col h-full w-60 shrink-0 border-r border-border-default bg-bg-panel">
      {/* Search */}
      <div className="px-3 pt-3 pb-2 shrink-0">
        <div className="relative">
          <VscSearch
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted"
            size={11}
            aria-hidden="true"
          />
          <input
            type="search"
            placeholder="Search threads…"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-7 pr-2 py-1.5 text-xs bg-bg-secondary border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent"
            aria-label="Search email threads"
          />
        </div>
      </div>

      {/* Thread list */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center text-text-muted text-xs">Loading…</div>
      ) : threads.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-2 text-text-muted">
          <VscMail size={24} aria-hidden="true" />
          <span className="text-xs">No threads found</span>
        </div>
      ) : (
        <ul className="flex-1 overflow-y-auto" role="list">
          {threads.map((thread) => {
            const isSelected = thread.thread_key === selectedKey;
            return (
              <li key={thread.thread_key}>
                <button
                  type="button"
                  onClick={() => onSelect(thread)}
                  className={`w-full text-left px-3 py-2.5 border-b border-border-default transition-colors ${
                    isSelected
                      ? 'bg-accent/10 border-l-2 border-l-accent'
                      : 'hover:bg-bg-secondary'
                  }`}
                  aria-current={isSelected ? 'true' : undefined}
                >
                  <div className="flex items-start gap-2">
                    {/* Avatar */}
                    <div className="w-7 h-7 rounded-full bg-accent/20 text-accent flex items-center justify-center text-[9px] font-bold shrink-0 mt-0.5">
                      {initials(thread.latest_sender || thread.participants[0] || '?')}
                    </div>

                    <div className="flex-1 min-w-0">
                      {/* Subject + time */}
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <span className="text-[11px] font-semibold text-text-primary truncate">
                          {thread.subject || '(no subject)'}
                        </span>
                        <span className="text-[9px] text-text-muted shrink-0">
                          {relativeTime(thread.latest_date)}
                        </span>
                      </div>

                      {/* Sender + count */}
                      <div className="flex items-center gap-1 text-[10px] text-text-secondary">
                        <span className="truncate">
                          {thread.latest_sender.split('@')[0]}
                        </span>
                        {thread.message_count > 1 && (
                          <span className="shrink-0 text-text-muted">· {thread.message_count}</span>
                        )}
                      </div>

                      {/* Badges row */}
                      <div className="flex items-center gap-1 mt-1 flex-wrap">
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded truncate max-w-[120px] ${attributionColors[thread.attribution_reason] ?? 'bg-bg-secondary text-text-muted'}`}
                          title={classificationLabel(thread.classification, thread.attribution_reason)}
                        >
                          {classificationLabel(thread.classification, thread.attribution_reason)}
                        </span>
                        {thread.has_draft_reply && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-orange-500/15 text-orange-400">
                            draft
                          </span>
                        )}
                        {thread.has_attachment && (
                          <VscAttach size={10} className="text-text-muted" aria-label="Has attachment" />
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
