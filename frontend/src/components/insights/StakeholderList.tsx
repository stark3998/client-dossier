import type { Stakeholder } from '@/types';

interface Props {
  stakeholders: Stakeholder[];
}

export function StakeholderList({ stakeholders }: Props) {
  if (stakeholders.length === 0) return null;

  return (
    <div className="bg-bg-secondary rounded-md p-3 border border-border-default">
      <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Key Stakeholders</h3>
      <div className="space-y-2">
        {stakeholders.map((s, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-accent/20 flex items-center justify-center text-[10px] font-bold text-accent shrink-0">
              {s.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-xs text-text-primary truncate">{s.name}</div>
              {s.title && <div className="text-[10px] text-text-muted truncate">{s.title}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
