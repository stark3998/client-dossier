// frontend/src/components/communication/EmailDetail.tsx
import { useEffect, useState } from 'react';
import { VscArrowLeft, VscEdit } from 'react-icons/vsc';
import { fetchEmail, triggerScan } from '../../hooks/useCommunication';
import type { ScannedEmail } from '../../types';

interface Props {
  emailId: string;
  clientName: string;
  onBack: () => void;
  onDraftCreated: () => void;
}

export function EmailDetail({ emailId, clientName, onBack, onDraftCreated }: Props) {
  const [email, setEmail] = useState<ScannedEmail | null>(null);
  const [loading, setLoading] = useState(true);
  const [drafting, setDrafting] = useState(false);
  const [draftDone, setDraftDone] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchEmail(clientName, emailId)
      .then(setEmail)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [clientName, emailId]);

  async function handleGenerateDraft() {
    setDrafting(true);
    try {
      await fetch(
        `/api/communication/${encodeURIComponent(clientName)}/drafts`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email_id: emailId }),
        }
      );
      setDraftDone(true);
      onDraftCreated();
    } catch (e) {
      console.error(e);
    } finally {
      setDrafting(false);
    }
  }

  if (loading) return <div className="p-6 text-text-muted text-sm">Loading…</div>;
  if (!email) return <div className="p-6 text-text-muted text-sm">Email not found.</div>;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 h-10 bg-bg-secondary border-b border-border-default shrink-0">
        <button type="button" onClick={onBack} aria-label="Back" className="text-text-muted hover:text-text-primary">
          <VscArrowLeft size={14} aria-hidden="true" />
        </button>
        <span className="text-xs font-medium text-text-primary truncate flex-1">{email.subject}</span>
        {!email.has_draft_reply && !draftDone && (
          <button
            type="button"
            onClick={handleGenerateDraft}
            disabled={drafting}
            className="flex items-center gap-1 px-2 py-1 text-[10px] rounded bg-accent text-white disabled:opacity-50"
          >
            <VscEdit size={10} aria-hidden="true" />
            {drafting ? 'Drafting…' : 'Generate Reply'}
          </button>
        )}
        {(email.has_draft_reply || draftDone) && (
          <span className="text-[10px] px-2 py-1 rounded bg-accent/10 text-accent">Draft exists</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
          <span className="text-text-muted">From</span>
          <span className="text-text-primary">{email.sender}</span>
          <span className="text-text-muted">To</span>
          <span className="text-text-secondary">{email.recipients.join(', ')}</span>
          <span className="text-text-muted">Date</span>
          <span className="text-text-secondary">{new Date(email.received_at).toLocaleString()}</span>
          <span className="text-text-muted">Folder</span>
          <span className="text-text-secondary">{email.folder} · {email.account}</span>
        </div>

        {email.has_attachment && email.attachment_names.length > 0 && (
          <div className="text-[10px] text-text-muted">
            Attachments: {email.attachment_names.join(', ')}
          </div>
        )}

        <div className="border-t border-border-default pt-3">
          <pre className="text-xs text-text-secondary whitespace-pre-wrap font-sans leading-relaxed">
            {email.body_full || email.body_preview}
          </pre>
        </div>
      </div>
    </div>
  );
}
