// frontend/src/components/communication/MeetingLogList.tsx
import { useState } from 'react';
import { VscCalendar, VscChevronDown, VscChevronRight, VscLoading } from 'react-icons/vsc';
import { fetchTranscript } from '../../hooks/useCommunication';
import type { MeetingLog } from '../../types';

interface Props {
  meetings: MeetingLog[];
  loading: boolean;
  onReload: () => void;
}

const responseColor: Record<string, string> = {
  accepted: 'bg-accent/10 text-accent',
  declined: 'bg-red-500/10 text-red-400',
  tentative: 'bg-yellow-500/10 text-yellow-400',
  none: 'bg-bg-panel text-text-muted',
};

export function MeetingLogList({ meetings, loading, onReload }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [fetchingTranscript, setFetchingTranscript] = useState<string | null>(null);

  async function handleFetchTranscript(clientName: string, meetingId: string) {
    setFetchingTranscript(meetingId);
    try {
      await fetchTranscript(clientName, meetingId);
      onReload();
    } finally {
      setFetchingTranscript(null);
    }
  }

  if (loading) return <div className="p-6 text-text-muted text-sm">Loading…</div>;
  if (meetings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-text-muted gap-2">
        <VscCalendar size={28} aria-hidden="true" />
        <span className="text-xs">No meetings logged</span>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-border-default" role="list">
      {meetings.map((m) => {
        const isExpanded = expanded === m.id;
        const isPast = new Date(m.start_time) < new Date();
        return (
          <li key={m.id} className="bg-bg-panel">
            <button
              type="button"
              onClick={() => setExpanded(isExpanded ? null : m.id)}
              className="w-full flex items-start gap-3 px-4 py-3 hover:bg-bg-secondary transition-colors text-left"
              aria-expanded={isExpanded}
            >
              <div className="shrink-0 mt-0.5">
                {isExpanded ? (
                  <VscChevronDown size={12} className="text-text-muted" aria-hidden="true" />
                ) : (
                  <VscChevronRight size={12} className="text-text-muted" aria-hidden="true" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-text-primary truncate">{m.subject || '(no subject)'}</span>
                  {m.is_teams_meeting && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 shrink-0">Teams</span>
                  )}
                </div>
                <div className="text-[10px] text-text-muted mt-0.5">
                  {new Date(m.start_time).toLocaleString()} · {m.attendees.length} attendee{m.attendees.length !== 1 ? 's' : ''}
                </div>
              </div>
              <span className={`text-[9px] px-1.5 py-0.5 rounded shrink-0 ${responseColor[m.my_response] ?? responseColor.none}`}>
                {m.my_response}
              </span>
            </button>

            {isExpanded && (
              <div className="px-4 pb-4 space-y-3 border-t border-border-default bg-bg-secondary">
                <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs pt-3">
                  <span className="text-text-muted">Organizer</span>
                  <span className="text-text-secondary">{m.organizer || '—'}</span>
                  <span className="text-text-muted">Location</span>
                  <span className="text-text-secondary">{m.location || '—'}</span>
                  {m.teams_join_url && (
                    <>
                      <span className="text-text-muted">Join URL</span>
                      <a href={m.teams_join_url} target="_blank" rel="noreferrer" className="text-accent text-xs truncate hover:underline">
                        Open in Teams
                      </a>
                    </>
                  )}
                </div>

                {/* Attendees */}
                <div>
                  <div className="text-[10px] text-text-muted uppercase tracking-wide mb-1">Attendees</div>
                  <div className="flex flex-wrap gap-1">
                    {m.attendees.map((a, i) => (
                      <span key={i} className={`text-[10px] px-1.5 py-0.5 rounded ${responseColor[a.response_status] ?? responseColor.none}`}>
                        {a.name || a.email}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Agenda */}
                {m.agenda && (
                  <div>
                    <div className="text-[10px] text-text-muted uppercase tracking-wide mb-1">Agenda</div>
                    <pre className="text-xs text-text-secondary whitespace-pre-wrap font-sans leading-relaxed line-clamp-6">
                      {m.agenda}
                    </pre>
                  </div>
                )}

                {/* Transcript */}
                {m.transcript_summary ? (
                  <div>
                    <div className="text-[10px] text-text-muted uppercase tracking-wide mb-1">Transcript Summary</div>
                    <p className="text-xs text-text-secondary leading-relaxed">{m.transcript_summary}</p>
                  </div>
                ) : isPast && m.is_teams_meeting && (
                  <button
                    type="button"
                    onClick={() => handleFetchTranscript(m.client_name, m.id)}
                    disabled={fetchingTranscript === m.id}
                    className="flex items-center gap-1 text-[10px] text-accent hover:underline disabled:opacity-50"
                  >
                    {fetchingTranscript === m.id && <VscLoading size={10} className="animate-spin" aria-hidden="true" />}
                    Fetch transcript
                  </button>
                )}

                {/* Action items */}
                {m.action_items_extracted.length > 0 && (
                  <div>
                    <div className="text-[10px] text-text-muted uppercase tracking-wide mb-1">Action Items</div>
                    <ul className="space-y-0.5">
                      {m.action_items_extracted.map((ai, i) => (
                        <li key={i} className="text-xs text-text-secondary flex gap-1.5">
                          <span className="text-text-muted mt-0.5">·</span>
                          {ai}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
