// frontend/src/components/insights/ProjectTracker.tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useEngagements } from '@/hooks/useEngagements';
import { VscArrowLeft } from 'react-icons/vsc';

const PHASES = ['discovery', 'design', 'execute', 'deliver', 'sustain'] as const;

export function ProjectTracker() {
  const { clientName } = useParams();
  const navigate = useNavigate();
  const { engagements, loading } = useEngagements();

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="flex items-center gap-3 px-6 h-12 bg-bg-secondary border-b border-border-default">
        <button type="button" onClick={() => navigate(`/clients/${clientName}`)} aria-label="Back" className="text-text-muted hover:text-text-primary">
          <VscArrowLeft size={16} aria-hidden="true" />
        </button>
        <h1 className="text-sm font-bold text-text-primary">Engagements — {decodeURIComponent(clientName || '')}</h1>
      </header>
      <main className="p-6">
        {loading ? <div className="text-text-muted">Loading...</div> : (
          <div className="flex gap-4 overflow-x-auto pb-4">
            {PHASES.map((phase) => {
              const items = engagements.filter((e) => e.phase === phase);
              return (
                <div key={phase} className="min-w-[220px] flex-shrink-0">
                  <div className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3 capitalize">{phase}</div>
                  <div className="space-y-2">
                    {items.map((e) => (
                      <div key={e.id} className="p-3 bg-bg-panel border border-border-default rounded-md">
                        <div className="text-xs font-medium text-text-primary">{e.name}</div>
                        <div className="text-[10px] text-text-muted mt-1">{e.description?.slice(0, 60)}</div>
                        <div className={`inline-block mt-1.5 px-1.5 py-0.5 text-[10px] rounded ${
                          e.status === 'active' ? 'bg-accent/10 text-accent' :
                          e.status === 'on-hold' ? 'bg-yellow-500/10 text-yellow-400' :
                          'bg-text-muted/10 text-text-muted'
                        }`}>{e.status}</div>
                      </div>
                    ))}
                    {items.length === 0 && <div className="text-[10px] text-text-muted p-3">No engagements</div>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
