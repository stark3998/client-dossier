// frontend/src/components/dashboard/HealthScoreIndicator.tsx
import { clsx } from 'clsx';

interface HealthScoreIndicatorProps {
  score: number;
  label?: string;
  size?: 'sm' | 'md';
}

function getStatusColor(score: number): string {
  if (score >= 70) return 'bg-status-green';
  if (score >= 50) return 'bg-status-amber';
  return 'bg-status-red';
}

function getStatusLabel(score: number): string {
  if (score >= 70) return 'Healthy';
  if (score >= 50) return 'At risk';
  return 'Critical';
}

/**
 * Small traffic-light circle that reflects a health score.
 * Green >= 70, amber >= 50, red < 50.
 */
export function HealthScoreIndicator({ score, label, size = 'md' }: HealthScoreIndicatorProps) {
  const dotSize = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';
  const statusColor = getStatusColor(score);
  const ariaLabel = label
    ? `${label}: ${score} - ${getStatusLabel(score)}`
    : `Score ${score} - ${getStatusLabel(score)}`;

  return (
    <span className="inline-flex items-center gap-1.5" aria-label={ariaLabel} role="status">
      <span
        className={clsx('rounded-full shrink-0', dotSize, statusColor)}
        aria-hidden="true"
      />
      {label && (
        <span className="text-xs text-text-secondary">{label}</span>
      )}
    </span>
  );
}
