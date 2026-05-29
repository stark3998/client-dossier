// frontend/src/components/notifications/NotificationDrawer.tsx
import { useCallback, useEffect } from 'react';
import { VscClose } from 'react-icons/vsc';
import { useClientStore } from '@/stores/clientStore';
import { NotificationItem } from './NotificationItem';

export function NotificationDrawer() {
  const open = useClientStore((s) => s.notificationDrawerOpen);
  const setOpen = useClientStore((s) => s.setNotificationDrawerOpen);
  const notifications = useClientStore((s) => s.notifications);
  const markRead = useClientStore((s) => s.markNotificationRead);
  const markAllRead = useClientStore((s) => s.markAllNotificationsRead);

  const close = useCallback(() => setOpen(false), [setOpen]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, close]);

  if (!open) return null;

  const handleItemClick = (id: string, targetRoute?: string) => {
    markRead(id);
    if (targetRoute) {
      close();
      // Navigation handled by caller or router — keep component pure
      window.location.hash = targetRoute;
    }
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/40"
        onClick={close}
        aria-hidden="true"
      />

      {/* Panel */}
      <aside
        role="dialog"
        aria-label="Notifications panel"
        className="fixed right-0 top-0 h-full w-96 z-50 bg-bg-secondary border-l border-border-default flex flex-col animate-slide-in-right"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
          <h2 className="text-base font-medium text-text-primary">Notifications</h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={markAllRead}
              className="text-xs text-accent hover:text-accent-bright transition-colors focus:outline-none focus:ring-2 focus:ring-accent-blue rounded px-1"
            >
              Mark all read
            </button>
            <button
              type="button"
              onClick={close}
              aria-label="Close notifications"
              className="p-1 rounded hover:bg-bg-hover text-text-secondary hover:text-text-primary transition-colors focus:outline-none focus:ring-2 focus:ring-accent-blue"
            >
              <VscClose className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <p className="text-sm text-text-muted text-center mt-12">
              No notifications yet
            </p>
          ) : (
            <div className="divide-y divide-border-default">
              {notifications.map((n) => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  onClick={() => handleItemClick(n.id, n.target_route)}
                />
              ))}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
