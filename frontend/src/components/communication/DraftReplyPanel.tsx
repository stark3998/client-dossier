// frontend/src/components/communication/DraftReplyPanel.tsx
import { useState } from 'react';
import { VscCheck, VscClose, VscEdit, VscLoading, VscMail } from 'react-icons/vsc';
import { useDrafts } from '../../hooks/useCommunication';
import type { DraftReply } from '../../types';

interface Props {
  clientName: string;
}

const statusBadge: Record<DraftReply['status'], string> = {
  pending_review: 'bg-yellow-500/10 text-yellow-400',
  edited: 'bg-accent/10 text-accent',
  pushed_to_outlook: 'bg-green-500/10 text-green-400',
  discarded: 'bg-bg-panel text-text-muted',
};

export function DraftReplyPanel({ clientName }: Props) {
  const { drafts, loading, updateDraft, approveDraft, submitFeedback, discardDraft } = useDrafts(clientName);
  const [selected, setSelected] = useState<DraftReply | null>(null);
  const [editBody, setEditBody] = useState('');
  const [editSubject, setEditSubject] = useState('');
  const [feedback, setFeedback] = useState('');
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);

  function openDraft(d: DraftReply) {
    setSelected(d);
    setEditBody(d.body);
    setEditSubject(d.subject);
    setFeedback('');
  }

  async function handleSave() {
    if (!selected) return;
    setSaving(true);
    try {
      await updateDraft(selected.id, { body: editBody, subject: editSubject });
      setSelected((prev) => prev ? { ...prev, body: editBody, subject: editSubject, status: 'edited' } : null);
    } finally {
      setSaving(false);
    }
  }

  async function handleApprove() {
    if (!selected) return;
    setApproving(true);
    try {
      await approveDraft(selected.id);
      setSelected((prev) => prev ? { ...prev, status: 'pushed_to_outlook' } : null);
    } finally {
      setApproving(false);
    }
  }

  async function handleFeedback() {
    if (!selected || !feedback.trim()) return;
    await submitFeedback(selected.id, feedback.trim());
    setFeedback('');
  }

  async function handleDiscard() {
    if (!selected) return;
    await discardDraft(selected.id);
    setSelected(null);
  }

  if (loading) return <div className="p-6 text-text-muted text-sm">Loading…</div>;

  if (selected) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-2 px-4 h-10 bg-bg-secondary border-b border-border-default shrink-0">
          <button type="button" onClick={() => setSelected(null)} aria-label="Back" className="text-text-muted hover:text-text-primary">
            <VscClose size={14} aria-hidden="true" />
          </button>
          <span className="flex-1 text-xs font-medium text-text-primary truncate">Draft: {selected.subject}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded ${statusBadge[selected.status]}`}>{selected.status.replace(/_/g, ' ')}</span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <div className="space-y-1.5">
            <label className="text-[10px] text-text-muted uppercase tracking-wide" htmlFor="draft-subject">Subject</label>
            <input
              id="draft-subject"
              type="text"
              value={editSubject}
              onChange={(e) => setEditSubject(e.target.value)}
              disabled={selected.status === 'pushed_to_outlook'}
              className="w-full px-2 py-1.5 text-xs bg-bg-secondary border border-border-default rounded text-text-primary focus:outline-none focus:border-accent disabled:opacity-50"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] text-text-muted uppercase tracking-wide" htmlFor="draft-to">To</label>
            <div className="text-xs text-text-secondary">{selected.to.join(', ')}</div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] text-text-muted uppercase tracking-wide" htmlFor="draft-body">Body</label>
            <textarea
              id="draft-body"
              value={editBody}
              onChange={(e) => setEditBody(e.target.value)}
              disabled={selected.status === 'pushed_to_outlook'}
              rows={10}
              className="w-full px-2 py-1.5 text-xs bg-bg-secondary border border-border-default rounded text-text-primary focus:outline-none focus:border-accent disabled:opacity-50 resize-none font-sans leading-relaxed"
            />
          </div>

          {selected.status !== 'pushed_to_outlook' && (
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-bg-secondary border border-border-default text-text-primary hover:border-accent disabled:opacity-50"
              >
                {saving ? <VscLoading size={11} className="animate-spin" aria-hidden="true" /> : <VscEdit size={11} aria-hidden="true" />}
                Save
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={approving}
                className="flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-accent text-white hover:bg-accent/90 disabled:opacity-50"
              >
                {approving ? <VscLoading size={11} className="animate-spin" aria-hidden="true" /> : <VscCheck size={11} aria-hidden="true" />}
                Push to Outlook
              </button>
              <button
                type="button"
                onClick={handleDiscard}
                className="flex items-center gap-1 px-2.5 py-1 text-xs rounded text-text-muted hover:text-red-400 ml-auto"
              >
                <VscClose size={11} aria-hidden="true" />
                Discard
              </button>
            </div>
          )}

          {/* Feedback */}
          <div className="border-t border-border-default pt-3 space-y-1.5">
            <label className="text-[10px] text-text-muted uppercase tracking-wide" htmlFor="draft-feedback">Feedback (improves future drafts)</label>
            <textarea
              id="draft-feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="e.g. 'Too formal, use first name' or 'Always mention project code'"
              rows={2}
              className="w-full px-2 py-1.5 text-xs bg-bg-secondary border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent resize-none"
            />
            <button
              type="button"
              onClick={handleFeedback}
              disabled={!feedback.trim()}
              className="px-2.5 py-1 text-xs rounded bg-bg-secondary border border-border-default text-text-primary hover:border-accent disabled:opacity-40"
            >
              Save Feedback
            </button>
            {selected.feedback && (
              <p className="text-[10px] text-text-muted">Previous: {selected.feedback}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {drafts.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-text-muted gap-2">
          <VscMail size={28} aria-hidden="true" />
          <span className="text-xs">No draft replies</span>
        </div>
      ) : (
        <ul className="divide-y divide-border-default" role="list">
          {drafts.map((d) => (
            <li key={d.id}>
              <button
                type="button"
                onClick={() => openDraft(d)}
                className="w-full flex items-start gap-3 px-4 py-3 hover:bg-bg-secondary transition-colors text-left"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-text-primary truncate">{d.subject}</div>
                  <div className="text-[10px] text-text-muted mt-0.5">To: {d.to.join(', ')}</div>
                </div>
                <span className={`text-[9px] px-1.5 py-0.5 rounded shrink-0 ${statusBadge[d.status]}`}>
                  {d.status.replace(/_/g, ' ')}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
