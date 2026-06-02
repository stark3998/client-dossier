import type { ClientMemory } from '@/types';

interface Props {
  memory: ClientMemory;
}

export function InsightsSummary({ memory }: Props) {
  return (
    <div className="bg-bg-secondary rounded-md p-3 border border-border-default">
      <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Client Overview</h3>
      <div className="space-y-1.5">
        <div className="text-sm font-medium text-text-primary">{memory.client_name}</div>
        {memory.industry && (
          <span className="inline-block px-2 py-0.5 text-[10px] rounded bg-accent/10 text-accent">{memory.industry}</span>
        )}
        {memory.financials_summary && (
          <p className="text-xs text-text-secondary">{memory.financials_summary}</p>
        )}
        {(memory.pain_points?.length ?? 0) > 0 && (
          <div>
            <span className="text-[10px] text-text-muted uppercase">Pain Points</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {memory.pain_points.map((p, i) => (
                <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-red-500/10 text-red-400">{p}</span>
              ))}
            </div>
          </div>
        )}
        {(memory.strategic_priorities?.length ?? 0) > 0 && (
          <div>
            <span className="text-[10px] text-text-muted uppercase">Priorities</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {memory.strategic_priorities.map((p, i) => (
                <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-accent-blue/10 text-accent-blue">{p}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
