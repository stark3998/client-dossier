interface Props {
  engagements: string[];
}

export function EngagementTimeline({ engagements }: Props) {
  if (engagements.length === 0) return null;

  return (
    <div className="bg-bg-secondary rounded-md p-3 border border-border-default">
      <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Active Engagements</h3>
      <div className="space-y-1.5">
        {engagements.map((eng, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
            <span className="text-xs text-text-primary">{eng}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
