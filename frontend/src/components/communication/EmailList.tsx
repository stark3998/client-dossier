// frontend/src/components/communication/EmailList.tsx
import { useState } from 'react';
import { VscAttach, VscMail, VscSearch } from 'react-icons/vsc';
import type { ScannedEmail } from '../../types';

interface Props {
  emails: ScannedEmail[];
  loading: boolean;
  onSelect: (email: ScannedEmail) => void;
  onSearch: (q: string) => void;
}

const attributionBadge: Record<string, string> = {
  domain_match: 'bg-accent/10 text-accent',
  keyword_match: 'bg-yellow-500/10 text-yellow-400',
  contact_match: 'bg-purple-500/10 text-purple-400',
};

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function EmailList({ emails, loading, onSelect, onSearch }: Props) {
  const [query, setQuery] = useState('');

  function handleSearch(q: string) {
    setQuery(q);
    onSearch(q);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-3 pb-2">
        <div className="relative">
          <VscSearch className="absolute left-2.5 top-2 text-text-muted" size={12} aria-hidden="true" />
          <input
            type="search"
            placeholder="Search emails..."
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-7 pr-3 py-1.5 text-xs bg-bg-secondary border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent"
            aria-label="Search emails"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-text-muted text-sm">Loading…</div>
      ) : emails.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-text-muted gap-2">
          <VscMail size={28} aria-hidden="true" />
          <span className="text-xs">No emails found</span>
        </div>
      ) : (
        <ul className="flex-1 overflow-y-auto divide-y divide-border-default" role="list">
          {emails.map((email) => (
            <li key={email.id}>
              <button
                type="button"
                onClick={() => onSelect(email)}
                className="w-full text-left px-4 py-3 hover:bg-bg-secondary transition-colors group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-xs font-medium text-text-primary truncate">{email.sender || '(no sender)'}</span>
                      {email.has_attachment && (
                        <VscAttach size={10} className="text-text-muted shrink-0" aria-label="Has attachment" />
                      )}
                    </div>
                    <div className="text-xs text-text-secondary truncate">{email.subject || '(no subject)'}</div>
                    <div className="text-[10px] text-text-muted mt-0.5 truncate">{email.body_preview}</div>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="text-[10px] text-text-muted">{relativeTime(email.received_at)}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${attributionBadge[email.attribution_reason] ?? 'bg-bg-panel text-text-muted'}`}>
                      {email.attribution_reason.replace('_', ' ')}
                    </span>
                    {email.has_draft_reply && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">draft</span>
                    )}
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
