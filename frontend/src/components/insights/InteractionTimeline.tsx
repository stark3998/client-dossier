// frontend/src/components/insights/InteractionTimeline.tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useTimeline } from '@/hooks/useTimeline';
import { VscArrowLeft, VscMail, VscCallOutgoing, VscPerson, VscFile } from 'react-icons/vsc';

const typeIcons: Record<string, typeof VscMail> = {
  meeting: VscPerson,
  call: VscCallOutgoing,
  email: VscMail,
  analysis: VscFile,
  status_update: VscFile,
};

export function InteractionTimeline() {
  const { clientName } = useParams();
  const navigate = useNavigate();
  const { events, loading } = useTimeline();

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="flex items-center gap-3 px-6 h-12 bg-bg-secondary border-b border-border-default">
        <button type="button" onClick={() => navigate(`/clients/${clientName}`)} aria-label="Back" className="text-text-muted hover:text-text-primary">
          <VscArrowLeft size={16} aria-hidden="true" />
        </button>
        <h1 className="text-sm font-bold text-text-primary">Timeline — {decodeURIComponent(clientName || '')}</h1>
      </header>
      <main className="max-w-3xl mx-auto p-6">
        {loading ? <div className="text-text-muted">Loading...</div> : events.length === 0 ? (
          <div className="text-text-muted text-sm">No events yet</div>
        ) : (
          <div className="relative">
            <div className="absolute left-5 top-0 bottom-0 w-px bg-border-default" />
            <div className="space-y-4">
              {events.map((ev) => {
                const Icon = typeIcons[ev.subtype] || typeIcons[ev.type] || VscFile;
                return (
                  <div key={ev.id} className="flex gap-4 relative">
                    <div className="w-10 h-10 rounded-full bg-bg-panel border border-border-default flex items-center justify-center shrink-0 z-10">
                      <Icon size={16} className="text-accent-blue" />
                    </div>
                    <div className="flex-1 p-3 bg-bg-panel border border-border-default rounded-md">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent-blue/10 text-accent-blue uppercase">{ev.type}</span>
                        <span className="text-[10px] text-text-muted">{ev.date?.split('T')[0]}</span>
                      </div>
                      <div className="text-xs text-text-primary mt-1">{ev.summary}</div>
                      {ev.participants && ev.participants.length > 0 && (
                        <div className="text-[10px] text-text-muted mt-1">Participants: {ev.participants.join(', ')}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
