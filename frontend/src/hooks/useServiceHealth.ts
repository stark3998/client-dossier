// frontend/src/hooks/useServiceHealth.ts
import { useEffect, useState } from 'react';
import { showToast } from '@/components/common/Toast';

interface ServiceCheck {
  label: string;
  status: 'ok' | 'not_configured' | 'error';
  detail?: string;
}

interface ReadyResponse {
  status: string;
  checks: Record<string, ServiceCheck>;
}

const DISPLAY_ORDER = [
  'cosmos', 'openai', 'search', 'agent', 'graph', 'web_search', 'onedrive', 'mcp',
];

export function useServiceHealth() {
  // null = unknown (still loading), true = reachable, false = offline
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      try {
        const res = await fetch('/ready');
        if (cancelled) return;
        if (!res.ok) {
          setBackendOnline(false);
          return;
        }
        setBackendOnline(true);
        const data: ReadyResponse = await res.json();

        const ordered = DISPLAY_ORDER
          .map(key => data.checks[key] ? { key, ...data.checks[key] } : null)
          .filter(Boolean) as (ServiceCheck & { key: string })[];

        // Show unknown keys last
        const known = new Set(DISPLAY_ORDER);
        Object.entries(data.checks).forEach(([key, check]) => {
          if (!known.has(key)) ordered.push({ key, ...check });
        });

        ordered.forEach((check, i) => {
          setTimeout(() => {
            if (cancelled) return;
            if (check.status === 'ok') {
              showToast({
                type: 'success',
                title: check.label,
                message: 'Service is healthy',
              });
            } else if (check.status === 'not_configured') {
              showToast({
                type: 'info',
                title: check.label,
                message: 'Not configured — feature unavailable',
              });
            } else {
              showToast({
                type: 'error',
                title: check.label,
                message: check.detail ?? 'Service error',
              });
            }
          }, i * 150);
        });
      } catch {
        if (!cancelled) setBackendOnline(false);
      }
    }

    run();
    return () => { cancelled = true; };
  }, []);

  return { backendOnline };
}
