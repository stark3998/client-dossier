import type { Engagement } from '@/types';

const statusColors: Record<string, string> = {
  active: 'bg-status-green/20 text-status-green',
  'on-hold': 'bg-status-amber/20 text-status-amber',
  completed: 'bg-text-muted/20 text-text-muted',
  cancelled: 'bg-status-red/20 text-status-red',
};

interface Props {
  engagement: Engagement;
  onClick: () => void;
  dragAttributes?: Record<string, unknown>;
  dragListeners?: Record<string, unknown>;
  style?: React.CSSProperties;
}

export default function KanbanCard({ engagement, onClick, dragAttributes, dragListeners, style }: Props) {
  return (
    <div
      className="bg-bg-panel border border-border-default rounded-md p-3 cursor-pointer hover:border-text-muted transition-colors"
      onClick={onClick}
      style={style}
      {...dragAttributes}
      {...dragListeners}
    >
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-text-primary truncate">{engagement.name}</h4>
        <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColors[engagement.status] || statusColors.active}`}>
          {engagement.status}
        </span>
      </div>

      {engagement.description && (
        <p className="text-xs text-text-secondary line-clamp-2 mb-2">{engagement.description}</p>
      )}

      <div className="flex items-center justify-between">
        {/* Team avatars */}
        <div className="flex -space-x-1">
          {engagement.team.slice(0, 3).map((member, i) => (
            <div
              key={i}
              className="w-5 h-5 rounded-full bg-accent/20 border border-bg-panel flex items-center justify-center text-[8px] text-accent font-medium"
              title={member}
            >
              {member.charAt(0).toUpperCase()}
            </div>
          ))}
          {engagement.team.length > 3 && (
            <div className="w-5 h-5 rounded-full bg-bg-hover border border-bg-panel flex items-center justify-center text-[8px] text-text-muted">
              +{engagement.team.length - 3}
            </div>
          )}
        </div>

        {/* Date */}
        {engagement.end_date && (
          <span className="text-[10px] text-text-muted font-mono">{engagement.end_date}</span>
        )}
      </div>
    </div>
  );
}
