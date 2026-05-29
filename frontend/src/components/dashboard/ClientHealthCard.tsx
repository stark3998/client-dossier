// frontend/src/components/dashboard/ClientHealthCard.tsx
import { clsx } from 'clsx';
import { VscWarning } from 'react-icons/vsc';
import type { ClientHealthReport } from '@/types';
import { HealthScoreIndicator } from './HealthScoreIndicator';

interface ClientHealthCardProps {
  clientName: string;
  health: ClientHealthReport | null;
  onClick: () => void;
}

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-status-green/20 text-status-green',
  B: 'bg-chart-1/20 text-chart-1',
  C: 'bg-status-amber/20 text-status-amber',
  D: 'bg-chart-4/20 text-chart-4',
  F: 'bg-status-red/20 text-status-red',
};

function MiniBar({ label, score }: { label: string; score: number }) {
  const fill = Math.max(0, Math.min(100, score));
  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] text-text-muted w-24 shrink-0 truncate">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-bg-primary overflow-hidden">
        <div
          className={clsx(
            'h-full rounded-full transition-all duration-300',
            fill >= 70 ? 'bg-status-green' : fill >= 50 ? 'bg-status-amber' : 'bg-status-red',
          )}
          style={{ width: `${fill}%` }}
        />
      </div>
      <span className="text-[11px] text-text-muted w-8 text-right tabular-nums">{fill}%</span>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="p-4 bg-bg-panel border border-border-default rounded-md animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-4 w-28 bg-bg-hover rounded" />
        <div className="h-5 w-8 bg-bg-hover rounded" />
      </div>
      <div className="space-y-2.5">
        <div className="h-1.5 w-full bg-bg-hover rounded-full" />
        <div className="h-1.5 w-full bg-bg-hover rounded-full" />
        <div className="h-1.5 w-full bg-bg-hover rounded-full" />
      </div>
    </div>
  );
}

/**
 * Card showing a single client's health summary with grade badge,
 * overall score, three mini-bars, and an alert count.
 */
export function ClientHealthCard({ clientName, health, onClick }: ClientHealthCardProps) {
  if (!health) return <Skeleton />;

  const alertCount = health.alerts.length;

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left p-4 bg-bg-panel border border-border-default rounded-md hover:border-accent/50 hover:bg-bg-hover transition-all group focus:outline-none focus:ring-2 focus:ring-accent/50"
      aria-label={`Open ${clientName} workspace. Grade ${health.grade}, score ${health.overall_score}`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-text-primary truncate">{clientName}</span>
          <HealthScoreIndicator score={health.overall_score} size="sm" />
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {alertCount > 0 && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-status-red/20 text-status-red">
              <VscWarning size={10} aria-hidden="true" />
              {alertCount}
            </span>
          )}
          <span
            className={clsx(
              'px-2 py-0.5 text-xs font-bold rounded',
              GRADE_COLORS[health.grade] ?? 'bg-bg-hover text-text-muted',
            )}
          >
            {health.grade}
          </span>
          <span className="text-xs text-text-muted tabular-nums">{health.overall_score}</span>
        </div>
      </div>

      {/* Mini bars */}
      <div className="space-y-1.5">
        <MiniBar label="Engagement" score={health.engagement_health.score} />
        <MiniBar label="Risk Posture" score={health.risk_posture.score} />
        <MiniBar label="Relationship" score={health.relationship_health.score} />
      </div>
    </button>
  );
}
