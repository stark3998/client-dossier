// frontend/src/hooks/useApiFetch.ts
import { useCallback } from 'react';
import { useMsal } from '@azure/msal-react';
import { apiFetch as _apiFetch, getAuthenticatedWsUrl as _getWsUrl } from '@/api/client';

const LOCAL_MODE = import.meta.env.VITE_LOCAL_MODE === 'true';

// Separate hook for live (MSAL) mode to avoid conditional hook call at the
// export level — LOCAL_MODE is a Vite compile-time constant so this assignment
// is safe and never changes at runtime.
function useLiveApiFetch() {
  const { instance, accounts } = useMsal();
  const account = accounts[0] ?? null;

  const fetchFn = useCallback(
    (url: string, opts?: RequestInit) => _apiFetch(url, opts ?? {}, instance, account),
    [instance, account],
  );

  const wsFn = useCallback(
    (path: string) => _getWsUrl(path, instance, account),
    [instance, account],
  );

  return { apiFetch: fetchFn, getAuthenticatedWsUrl: wsFn };
}

function useLocalApiFetch() {
  const fetchFn = useCallback(
    (url: string, opts?: RequestInit) => fetch(url, opts ?? {}),
    [],
  );

  const wsFn = useCallback(
    (path: string) =>
      Promise.resolve(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${path}`),
    [],
  );

  return { apiFetch: fetchFn, getAuthenticatedWsUrl: wsFn };
}

/**
 * Returns authenticated `apiFetch` and `getAuthenticatedWsUrl` helpers.
 *
 * In LOCAL_MODE (VITE_LOCAL_MODE=true) MsalProvider is not rendered, so
 * useMsal() would throw. The export is statically assigned to the correct
 * implementation based on the compile-time constant — no conditional hook call
 * occurs at runtime.
 */
export const useApiFetch = LOCAL_MODE ? useLocalApiFetch : useLiveApiFetch;
