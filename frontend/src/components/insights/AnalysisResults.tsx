// frontend/src/components/insights/AnalysisResults.tsx
import { useParams, useNavigate } from 'react-router-dom';
import { useAnalysis } from '@/hooks/useAnalysis';
import { VscArrowLeft, VscFile } from 'react-icons/vsc';

export function AnalysisResults() {
  const { clientName } = useParams();
  const navigate = useNavigate();
  const { results, loading } = useAnalysis();

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="flex items-center gap-3 px-6 h-12 bg-bg-secondary border-b border-border-default">
        <button type="button" onClick={() => navigate(`/clients/${clientName}`)} aria-label="Back" className="text-text-muted hover:text-text-primary">
          <VscArrowLeft size={16} aria-hidden="true" />
        </button>
        <h1 className="text-sm font-bold text-text-primary">Document Analysis — {decodeURIComponent(clientName || '')}</h1>
      </header>
      <main className="max-w-4xl mx-auto p-6">
        {loading ? <div className="text-text-muted">Loading...</div> : results.length === 0 ? (
          <div className="text-text-muted text-sm">No documents analyzed yet. Upload files to trigger auto-analysis.</div>
        ) : (
          <div className="space-y-4">
            {results.map((r) => (
              <div key={r.id} className="p-4 bg-bg-panel border border-border-default rounded-md">
                <div className="flex items-center gap-2 mb-2">
                  <VscFile size={16} className="text-accent-blue" />
                  <span className="text-sm font-medium text-text-primary">{r.file_path.split('/').pop()}</span>
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-accent-blue/10 text-accent-blue">{r.doc_type}</span>
                  <span className="text-[10px] text-text-muted ml-auto">{r.analyzed_at?.split('T')[0]}</span>
                </div>
                <p className="text-xs text-text-secondary mb-3">{r.analysis_summary}</p>

                {r.extracted_stakeholders.length > 0 && (
                  <div className="mb-2">
                    <span className="text-[10px] text-text-muted uppercase">Stakeholders ({r.extracted_stakeholders.length})</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {r.extracted_stakeholders.map((s, i) => (
                        <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-accent/10 text-accent">
                          {s.name}{s.title ? ` — ${s.title}` : ''}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {r.extracted_actions.length > 0 && (
                  <div className="mb-2">
                    <span className="text-[10px] text-text-muted uppercase">Action Items ({r.extracted_actions.length})</span>
                    <ul className="mt-1 space-y-0.5">
                      {r.extracted_actions.map((a, i) => (
                        <li key={i} className="text-xs text-text-secondary flex items-start gap-1.5">
                          <span className="text-accent mt-0.5">-</span>
                          <span>{a.description}{a.owner ? ` (${a.owner})` : ''}{a.due_date ? ` — Due: ${a.due_date}` : ''}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {r.extracted_risks.length > 0 && (
                  <div className="mb-2">
                    <span className="text-[10px] text-text-muted uppercase">Risks ({r.extracted_risks.length})</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {r.extracted_risks.map((risk, i) => (
                        <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-red-500/10 text-red-400">{risk.description}</span>
                      ))}
                    </div>
                  </div>
                )}

                {r.key_topics.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {r.key_topics.map((t, i) => (
                      <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-bg-secondary text-text-muted">{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
