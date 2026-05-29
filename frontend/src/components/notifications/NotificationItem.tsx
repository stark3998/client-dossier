// frontend/src/components/notifications/NotificationItem.tsx
import { formatDistanceToNow } from 'date-fns';
import type { Notification } from '@/types';

const ACCENT_COLORS: Record<Notification['type'], string> = {
  analysis_complete: 'border-l-accent-blue',
  overdue_alert: 'border-l-status-red',
  risk_escalation: 'border-l-status-red',
  memory_updated: 'border-l-accent',
  engagement_phase_change: 'border-l-status-amber',
};

interface Props {
  notification: Notification;
  onClick?: () => void;
}

export function NotificationItem({ notification, onClick }: Props) {
  const accent = ACCENT_COLORS[notification.type];
  const bgClass = notification.read ? 'bg-transparent' : 'bg-bg-hover';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left border-l-2 ${accent} ${bgClass} px-3 py-2.5 hover:bg-bg-hover transition-colors focus:outline-none focus:ring-2 focus:ring-accent-blue focus:ring-inset`}
    >
      <p className="text-sm font-medium text-text-primary leading-snug">
        {notification.title}
      </p>
      <p className="text-sm text-text-secondary mt-0.5 line-clamp-2">
        {notification.description}
      </p>
      <p className="text-xs text-text-muted mt-1">
        {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
      </p>
    </button>
  );
}
