// frontend/src/components/insights/RiskRegister.tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useEngagements } from '@/hooks/useEngagements';
import { VscArrowLeft } from 'react-icons/vsc';

export function RiskRegister() {
  const { clientName } = useParams();
  const navigate = useNavigate();
  const { risks, loading } = useEngagements();

  const severityColor = (p: number, i: number) => {
    const score = p * i;
    if (score >= 15) return 'text-red-400 bg-red-500/10';
    if (score >= 8) return 'text-yellow-400 bg-yellow-500/10';
    return 'text-accent bg-accent/10';
  };

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="flex items-center gap-3 px-6 h-12 bg-bg-secondary border-b border-border-default">
        <button type="button" onClick={() => navigate(`/clients/${clientName}`)} className="text-text-muted hover:text-text-primary">
          <VscArrowLeft size={16} />
        </button>
        <h1 className="text-sm font-bold text-text-primary">Risk Register — {decodeURIComponent(clientName || '')}</h1>
      </header>
      <main className="p-6">
        {loading ? <div className="text-text-muted">Loading...</div> : risks.length === 0 ? (
          <div className="text-text-muted text-sm">No risks recorded</div>
        ) : (
          <div className="space-y-2">
            {risks.map((r) => (
              <div key={r.id} className="p-4 bg-bg-panel border border-border-default rounded-md flex items-start gap-4">
                <div className={`px-2 py-1 rounded text-xs font-mono font-bold ${severityColor(r.probability, r.impact)}`}>
                  {r.probability}x{r.impact}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-text-primary">{r.description}</div>
                  {r.mitigation && <div className="text-xs text-text-secondary mt-1">Mitigation: {r.mitigation}</div>}
                  <div className="flex gap-2 mt-1.5">
                    <span className={`px-1.5 py-0.5 text-[10px] rounded ${
                      r.status === 'open' ? 'bg-red-500/10 text-red-400' :
                      r.status === 'mitigating' ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-accent/10 text-accent'
                    }`}>{r.status}</span>
                    <span className="text-[10px] text-text-muted">{r.category}</span>
                    {r.owner && <span className="text-[10px] text-text-muted">Owner: {r.owner}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
