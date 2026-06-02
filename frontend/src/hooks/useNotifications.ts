// frontend/src/hooks/useNotifications.ts
import { useRef, useCallback, useEffect } from 'react';
import { useClientStore } from '@/stores/clientStore';
import { useApiFetch } from '@/hooks/useApiFetch';
import { showToast } from '@/components/common/Toast';
import type { ClientEvent, Notification } from '@/types';

const EVENT_TYPE_TO_NOTIFICATION: Record<string, Notification['type']> = {
  analysis_complete: 'analysis_complete',
  overdue_alert: 'overdue_alert',
  risk_escalation: 'risk_escalation',
  memory_updated: 'memory_updated',
  engagement_phase_change: 'engagement_phase_change',
};

const SEVERITY_TO_PRIORITY: Record<ClientEvent['severity'], Notification['priority']> = {
  info: 'low',
  warning: 'medium',
  critical: 'high',
};

function toNotification(event: ClientEvent): Notification {
  return {
    id: event.id,
    type: EVENT_TYPE_TO_NOTIFICATION[event.event_type] ?? 'memory_updated',
    title: `[${event.client_name}] ${event.entity_type}`,
    description: event.summary,
    timestamp: event.created_at,
    read: false,
    client_name: event.client_name,
    priority: SEVERITY_TO_PRIORITY[event.severity],
  };
}

/** Connects to the /ws/notifications WebSocket and dispatches incoming events to the store. */
export function useNotifications() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { addNotification } = useClientStore();
  const { getAuthenticatedWsUrl } = useApiFetch();

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = await getAuthenticatedWsUrl('/ws/notifications');

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const clientEvent: ClientEvent = JSON.parse(event.data as string);
        const notification = toNotification(clientEvent);
        addNotification(notification);

        if (clientEvent.severity === 'critical') {
          showToast({
            type: 'error',
            title: notification.title,
            message: notification.description,
          });
        }
      } catch (err) {
        console.error('Failed to parse notification event:', err);
      }
    };

    ws.onclose = () => {
      reconnectTimerRef.current = setTimeout(() => { connect().catch(console.error); }, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [addNotification, getAuthenticatedWsUrl]);

  useEffect(() => {
    connect().catch(console.error);
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);
}
