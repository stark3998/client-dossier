// frontend/src/components/notifications/NotificationBell.tsx
import { VscBell } from 'react-icons/vsc';
import { useClientStore } from '@/stores/clientStore';

export function NotificationBell() {
  const unreadCount = useClientStore((s) => s.unreadCount);
  const drawerOpen = useClientStore((s) => s.notificationDrawerOpen);
  const setDrawerOpen = useClientStore((s) => s.setNotificationDrawerOpen);

  return (
    <button
      type="button"
      aria-label="Notifications"
      onClick={() => setDrawerOpen(!drawerOpen)}
      className="relative p-2 rounded-md text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors focus:outline-none focus:ring-2 focus:ring-accent-blue"
    >
      <VscBell className="w-5 h-5" />
      {unreadCount > 0 && (
        <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-4 h-4 px-1 rounded-full bg-status-red text-white text-xs font-medium leading-none">
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
    </button>
  );
}
