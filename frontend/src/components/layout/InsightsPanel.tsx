// frontend/src/components/layout/InsightsPanel.tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInsights } from '@/hooks/useInsights';
import { useEngagements } from '@/hooks/useEngagements';
import { useAnalysis } from '@/hooks/useAnalysis';
import { useTimeline } from '@/hooks/useTimeline';
import { useClientStore } from '@/stores/clientStore';
import { InsightsSummary } from '@/components/insights/InsightsSummary';
import { StakeholderList } from '@/components/insights/StakeholderList';
import { ActionItems } from '@/components/insights/ActionItems';
import { VscArrowRight } from 'react-icons/vsc';
import { useCommSummary } from '@/hooks/useCommunication';
import type { CommSummary } from '@/types';

export function InsightsPanel() {
  const navigate = useNavigate();
  const { activeClient } = useClientStore();
  const { memory, isLoading } = useInsights();
  const { engagements, risks } = useEngagements();
  const { results: analyses } = useAnalysis();
  const { events } = useTimeline();
  const [commSummary, setCommSummary] = useState<CommSummary | null>(null);
  const fetchCommSummary = useCommSummary();

  useEffect(() => {
    if (!activeClient) return;
    fetchCommSummary(activeClient).then(setCommSummary).catch(() => {});
  }, [activeClient, fetchCommSummary]);

  const clientPath = activeClient ? `/clients/${encodeURIComponent(activeClient)}` : '';

  if (!activeClient) {
    return (
      <div className="flex flex-col h-full bg-bg-panel">
        <div className="flex items-center px-3 h-10 border-b border-border-default shrink-0">
          <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Key Insights</span>
        </div>
        <div className="p-3 text-text-muted text-sm">Select a client to view insights</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-bg-panel">
      <div className="flex items-center px-3 h-10 border-b border-border-default shrink-0">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Key Insights</span>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Memory-dependent insight content */}
        {memory ? (
          <>
            <InsightsSummary memory={memory} />
            <StakeholderList stakeholders={memory.key_stakeholders} />
            <ActionItems items={memory.open_action_items} clientName={memory.client_name} />
          </>
        ) : isLoading ? (
          <div className="text-text-muted text-xs py-2">Loading insights...</div>
        ) : null}

        {/* Nav cards — always visible once a client is selected */}
        <NavCard
          title="Engagements"
          count={engagements.length}
          subtitle={engagements.filter((e) => e.status === 'active').length + ' active'}
          onClick={() => navigate(`${clientPath}/engagements`)}
        />
        <NavCard
          title="Risk Register"
          count={risks.length}
          subtitle={risks.filter((r) => r.status === 'open').length + ' open'}
          onClick={() => navigate(`${clientPath}/risks`)}
          color={risks.some((r) => r.probability * r.impact >= 15) ? 'red' : undefined}
        />
        <NavCard
          title="Timeline"
          count={events.length}
          subtitle={events.length > 0 ? `Latest: ${events[0]?.date?.split('T')[0] || ''}` : 'No events'}
          onClick={() => navigate(`${clientPath}/timeline`)}
        />
        <NavCard
          title="Document Analysis"
          count={analyses.length}
          subtitle={analyses.length > 0 ? `Last: ${analyses[0]?.doc_type || 'unknown'}` : 'No analyses'}
          onClick={() => navigate(`${clientPath}/analysis`)}
        />
        <NavCard
          title="Communications"
          count={commSummary?.emails_last_7d ?? 0}
          subtitle={
            commSummary
              ? `${commSummary.pending_drafts} draft${commSummary.pending_drafts !== 1 ? 's' : ''} · ${commSummary.upcoming_meetings} upcoming`
              : 'Emails (7d)'
          }
          onClick={() => navigate(`${clientPath}/communications`)}
          color={commSummary && commSummary.pending_drafts > 0 ? 'yellow' : undefined}
        />
        <NavCard
          title="Settings"
          count={0}
          subtitle="Profile · Comms · Engagements"
          onClick={() => navigate(`${clientPath}/settings`)}
        />
      </div>
    </div>
  );
}

function NavCard({ title, count, subtitle, onClick, color }: {
  title: string; count: number; subtitle: string; onClick: () => void; color?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full p-3 bg-bg-secondary rounded-md border border-border-default hover:border-accent/30 transition-colors text-left group"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">{title}</span>
        <VscArrowRight size={14} className="text-text-muted group-hover:text-accent transition-colors" />
      </div>
      <div className="flex items-baseline gap-2 mt-1">
        <span className={`text-lg font-bold ${color === 'red' ? 'text-red-400' : color === 'yellow' ? 'text-yellow-400' : 'text-text-primary'}`}>{count}</span>
        <span className="text-[10px] text-text-muted">{subtitle}</span>
      </div>
    </button>
  );
}
