// frontend/src/components/search/SearchResultCard.tsx
import { VscMail, VscAttach } from 'react-icons/vsc';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import type { InboxSearchResult } from '@/types';

interface Props {
  result: InboxSearchResult;
}

export function SearchResultCard({ result }: Props) {
  const navigate = useNavigate();

  const timeAgo = result.received_at
    ? formatDistanceToNow(new Date(result.received_at), { addSuffix: true })
    : '';

  return (
    <div className="bg-bg-secondary rounded-md border border-border-default p-3 space-y-1.5 hover:border-accent/30 transition-colors">
      {/* Subject + time */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <VscMail size={12} className="text-text-muted shrink-0 mt-0.5" aria-hidden="true" />
          <span className="text-xs font-medium text-text-primary truncate">
            {result.subject || '(no subject)'}
          </span>
        </div>
        <span className="text-[10px] text-text-muted shrink-0">{timeAgo}</span>
      </div>

      {/* Sender */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-text-muted truncate">
          {result.sender_name ? `${result.sender_name} <${result.sender}>` : result.sender}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          {result.has_attachment && (
            <VscAttach size={10} className="text-text-muted" aria-hidden="true" />
          )}
          {result.folder && (
            <span className="text-[9px] text-text-muted bg-bg-panel px-1 py-0.5 rounded">
              {result.folder}
            </span>
          )}
        </div>
      </div>

      {/* Body preview */}
      {result.body_preview && (
        <p className="text-[10px] text-text-muted line-clamp-2">{result.body_preview}</p>
      )}

      {/* Client badge */}
      {result.client_name && result.client_path && (
        <button
          type="button"
          onClick={() => navigate(result.client_path!)}
          className="inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded bg-accent/15 text-accent hover:bg-accent/25 transition-colors"
          aria-label={`Go to client ${result.client_name}`}
        >
          {result.client_name}
        </button>
      )}
    </div>
  );
}
