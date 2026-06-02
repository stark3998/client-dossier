// frontend/src/components/communication/ThreadDetail.tsx
import { useState } from 'react';
import {
  VscAttach,
  VscChevronDown,
  VscChevronRight,
  VscLoading,
  VscMail,
  VscReply,
} from 'react-icons/vsc';
import type { ScannedEmail } from '../../types';

interface Props {
  emails: ScannedEmail[];
  subject: string;
  loading: boolean;
  clientName: string;
  onGenerateReply: (emailId: string) => void;
}

function initials(email: string): string {
  const name = email.split('@')[0].replace(/[._]/g, ' ');
  const parts = name.split(' ').filter(Boolean);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function avatarColor(email: string): string {
  const colors = [
    'bg-blue-500/20 text-blue-400',
    'bg-purple-500/20 text-purple-400',
    'bg-green-500/20 text-green-400',
    'bg-orange-500/20 text-orange-400',
    'bg-pink-500/20 text-pink-400',
  ];
  let hash = 0;
  for (const c of email) hash = (hash * 31 + c.charCodeAt(0)) & 0xffff;
  return colors[hash % colors.length];
}

function EmailCard({
  email,
  defaultExpanded,
  onReply,
}: {
  email: ScannedEmail;
  defaultExpanded: boolean;
  onReply: () => void;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const senderName = email.sender.split('@')[0].replace(/[._]/g, ' ');
  const dateStr = new Date(email.received_at).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="border border-border-default rounded-md overflow-hidden bg-bg-panel">
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-bg-secondary transition-colors text-left"
        aria-expanded={expanded}
      >
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${avatarColor(email.sender)}`}>
          {initials(email.sender)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-text-primary">{senderName}</span>
            <span className="text-[10px] text-text-muted">{email.sender}</span>
          </div>
          {!expanded && (
            <div className="text-[10px] text-text-muted truncate mt-0.5">
              {email.body_preview}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {email.has_attachment && (
            <VscAttach size={12} className="text-text-muted" aria-label="Has attachment" />
          )}
          <span className="text-[10px] text-text-muted">{dateStr}</span>
          {expanded ? (
            <VscChevronDown size={12} className="text-text-muted" aria-hidden="true" />
          ) : (
            <VscChevronRight size={12} className="text-text-muted" aria-hidden="true" />
          )}
        </div>
      </button>

      {/* Body */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-border-default">
          {/* To line */}
          <div className="flex gap-2 text-[10px] text-text-muted py-2 border-b border-border-default mb-3">
            <span>To:</span>
            <span className="text-text-secondary">{email.recipients.join(', ')}</span>
          </div>

          {/* Attachments */}
          {email.has_attachment && email.attachment_names.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-3">
              {email.attachment_names.map((name) => (
                <span
                  key={name}
                  className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-bg-secondary text-text-secondary"
                >
                  <VscAttach size={9} aria-hidden="true" />
                  {name}
                </span>
              ))}
            </div>
          )}

          {/* Body */}
          <pre className="text-xs text-text-secondary whitespace-pre-wrap font-sans leading-relaxed">
            {email.body_full || email.body_preview}
          </pre>

          {/* Actions */}
          <div className="flex gap-2 mt-4 pt-3 border-t border-border-default">
            <button
              type="button"
              onClick={onReply}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-accent text-white hover:bg-accent/90 transition-colors"
            >
              <VscReply size={11} aria-hidden="true" />
              Generate Reply
            </button>
            {email.folder && (
              <span className="text-[10px] text-text-muted self-center">
                {email.folder} · {email.account}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function ThreadDetail({ emails, subject, loading, clientName, onGenerateReply }: Props) {
  const [generatingReply, setGeneratingReply] = useState<string | null>(null);

  async function handleGenerateReply(emailId: string) {
    setGeneratingReply(emailId);
    try {
      await fetch(
        `/api/communication/${encodeURIComponent(clientName)}/drafts`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email_id: emailId }),
        }
      );
      onGenerateReply(emailId);
    } catch (e) {
      console.error('Draft generation failed:', e);
    } finally {
      setGeneratingReply(null);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-muted gap-2">
        <VscLoading size={16} className="animate-spin" aria-hidden="true" />
        <span className="text-sm">Loading thread…</span>
      </div>
    );
  }

  if (emails.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-text-muted gap-2">
        <VscMail size={32} aria-hidden="true" />
        <span className="text-sm">Select a thread to read</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* Thread subject header */}
      <div className="px-5 py-3 border-b border-border-default shrink-0 bg-bg-secondary">
        <h2 className="text-sm font-semibold text-text-primary truncate">{subject}</h2>
        <div className="text-[10px] text-text-muted mt-0.5">
          {emails.length} message{emails.length !== 1 ? 's' : ''} ·{' '}
          {[...new Set(emails.map((e) => e.sender))].length} participant
          {[...new Set(emails.map((e) => e.sender))].length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {emails.map((email, idx) => (
          <div key={email.id} className="relative">
            {generatingReply === email.id && (
              <div className="absolute inset-0 bg-bg-primary/50 flex items-center justify-center rounded-md z-10">
                <VscLoading size={16} className="animate-spin text-accent" aria-hidden="true" />
              </div>
            )}
            <EmailCard
              email={email}
              defaultExpanded={idx === emails.length - 1}
              onReply={() => handleGenerateReply(email.id)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
