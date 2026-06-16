import { useEffect, useState } from 'react';
import { VscArrowLeft, VscMail, VscCalendar, VscLoading } from 'react-icons/vsc';
import { useApiFetch } from '@/hooks/useApiFetch';
import type { Stakeholder, ScannedEmail, MeetingLog } from '@/types';
import { formatDistanceToNow } from 'date-fns';

interface Props {
  stakeholder: Stakeholder;
  clientName: string;
  onClose: () => void;
}

function initials(name: string) {
  return name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase();
}

export function StakeholderDrawer({ stakeholder, clientName, onClose }: Props) {
  const { apiFetch } = useApiFetch();
  const [summary, setSummary] = useState('');
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [emails, setEmails] = useState<ScannedEmail[]>([]);
  const [meetings, setMeetings] = useState<MeetingLog[]>([]);
  const [loadingComms, setLoadingComms] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchSummary = async () => {
      setLoadingSummary(true);
      try {
        const res = await apiFetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'message',
            content: `Provide a concise professional summary of ${stakeholder.name} in the context of client ${clientName}. Cover: their role and seniority, key topics or projects they are involved in, any recent communications or meetings, and any open action items related to them. Keep it to 4–5 sentences.`,
            client_name: clientName,
          }),
        });
        const data = await res.json();
        if (!cancelled) {
          setSummary(data.content ?? data.response ?? data.message ?? '');
        }
      } catch {
        if (!cancelled) setSummary('');
      } finally {
        if (!cancelled) setLoadingSummary(false);
      }
    };

    const fetchComms = async () => {
      setLoadingComms(true);
      try {
        const searchTerm = encodeURIComponent(stakeholder.email ?? stakeholder.name);
        const encoded = encodeURIComponent(clientName);
        const [eRes, mRes] = await Promise.all([
          apiFetch(`/api/communication/${encoded}/emails?search=${searchTerm}&days=180`),
          apiFetch(`/api/communication/${encoded}/meetings?days=180`),
        ]);
        const eData = await eRes.json();
        const mData = await mRes.json();

        const emailList: ScannedEmail[] = Array.isArray(eData) ? eData : (eData.emails ?? []);
        const meetingList: MeetingLog[] = Array.isArray(mData) ? mData : (mData.meetings ?? []);

        const nameLower = stakeholder.name.toLowerCase();
        const emailLower = (stakeholder.email ?? '').toLowerCase();

        const filteredMeetings = meetingList.filter((m) =>
          m.attendees?.some(
            (a) =>
              (emailLower && a.email?.toLowerCase().includes(emailLower)) ||
              a.name?.toLowerCase().includes(nameLower),
          ),
        );

        if (!cancelled) {
          setEmails(emailList.slice(0, 20));
          setMeetings(filteredMeetings.slice(0, 10));
        }
      } catch {
        // silently fail — comms may not be set up
      } finally {
        if (!cancelled) setLoadingComms(false);
      }
    };

    fetchSummary();
    fetchComms();

    return () => { cancelled = true; };
  }, [stakeholder, clientName]);

  return (
    <div className="flex flex-col h-full bg-bg-panel">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 h-10 border-b border-border-default shrink-0">
        <button
          type="button"
          onClick={onClose}
          className="text-text-muted hover:text-text-primary transition-colors"
          aria-label="Back to insights"
        >
          <VscArrowLeft size={14} aria-hidden="true" />
        </button>
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider truncate">
          {stakeholder.name}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Identity card */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center text-sm font-bold text-accent shrink-0">
            {initials(stakeholder.name)}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-text-primary">{stakeholder.name}</div>
            {stakeholder.title && (
              <div className="text-xs text-text-muted">{stakeholder.title}</div>
            )}
            {stakeholder.email && (
              <div className="text-[10px] text-accent truncate">{stakeholder.email}</div>
            )}
          </div>
        </div>

        {/* AI Summary */}
        <div className="bg-bg-secondary rounded-md p-3 border border-border-default space-y-1.5">
          <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">AI Summary</span>
          {loadingSummary ? (
            <div className="flex items-center gap-2 text-text-muted">
              <VscLoading size={11} className="animate-spin" aria-hidden="true" />
              <span className="text-xs">Generating…</span>
            </div>
          ) : summary ? (
            <p className="text-xs text-text-secondary leading-relaxed">{summary}</p>
          ) : (
            <p className="text-xs text-text-muted italic">No context available yet. Ingest documents and run a scan to build a profile.</p>
          )}
        </div>

        {/* Emails */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <VscMail size={11} className="text-text-muted" aria-hidden="true" />
            <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
              Recent Emails
              {!loadingComms && <span className="ml-1 font-normal normal-case tracking-normal">({emails.length})</span>}
            </span>
          </div>
          {loadingComms ? (
            <div className="flex items-center gap-2 text-text-muted pl-1">
              <VscLoading size={11} className="animate-spin" aria-hidden="true" />
              <span className="text-xs">Loading…</span>
            </div>
          ) : emails.length === 0 ? (
            <p className="text-xs text-text-muted pl-1">No emails found. Configure communication scanning to see emails.</p>
          ) : (
            <div className="space-y-1.5">
              {emails.map((e) => (
                <div
                  key={e.id}
                  className="bg-bg-secondary rounded p-2.5 border border-border-default space-y-0.5"
                >
                  <div className="text-xs text-text-primary truncate">{e.subject || '(no subject)'}</div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] text-text-muted truncate">{e.sender}</span>
                    <span className="text-[10px] text-text-muted shrink-0">
                      {formatDistanceToNow(new Date(e.received_at), { addSuffix: true })}
                    </span>
                  </div>
                  {e.body_preview && (
                    <p className="text-[10px] text-text-muted line-clamp-2 mt-0.5">{e.body_preview}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Meetings */}
        {!loadingComms && meetings.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5">
              <VscCalendar size={11} className="text-text-muted" aria-hidden="true" />
              <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Meetings <span className="ml-1 font-normal normal-case tracking-normal">({meetings.length})</span>
              </span>
            </div>
            <div className="space-y-1.5">
              {meetings.map((m) => (
                <div
                  key={m.id}
                  className="bg-bg-secondary rounded p-2.5 border border-border-default space-y-0.5"
                >
                  <div className="text-xs text-text-primary truncate">{m.subject}</div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] text-text-muted">
                      {m.attendees?.length ?? 0} attendees
                    </span>
                    <span className="text-[10px] text-text-muted shrink-0">
                      {formatDistanceToNow(new Date(m.start_time), { addSuffix: true })}
                    </span>
                  </div>
                  {m.transcript_summary && (
                    <p className="text-[10px] text-text-muted line-clamp-2 mt-0.5">{m.transcript_summary}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
