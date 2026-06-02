// frontend/src/api/client.ts
import { IPublicClientApplication, AccountInfo, InteractionRequiredAuthError } from '@azure/msal-browser';
import { backendRequest } from '@/auth/msalConfig';
import { showToast } from '@/components/common/Toast';

const LOCAL_MODE = import.meta.env.VITE_LOCAL_MODE === 'true';

let _v1ToastShown = false;
function warnIfV1Token(response: Response) {
  if (!_v1ToastShown && response.headers.get('X-Token-Version') === '1') {
    _v1ToastShown = true;
    showToast({
      type: 'info',
      title: 'Upgrade to v2.0 tokens',
      message: 'Your access token is v1.0. Set accessTokenAcceptedVersion: 2 in the Entra app manifest to switch to v2.0.',
    });
  }
}

/**
 * Authenticated fetch wrapper. Acquires a Bearer token silently before each
 * request. In LOCAL_MODE the token step is skipped entirely.
 */
export async function apiFetch(
  url: string,
  options: RequestInit = {},
  msalInstance: IPublicClientApplication,
  account: AccountInfo | null,
): Promise<Response> {
  if (LOCAL_MODE) return fetch(url, options);

  let token: string;
  try {
    const result = await msalInstance.acquireTokenSilent({ ...backendRequest, account: account! });
    token = result.accessToken;
  } catch (err) {
    if (err instanceof InteractionRequiredAuthError) {
      await msalInstance.acquireTokenRedirect(backendRequest);
      throw err;
    }
    throw err;
  }

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(url, { ...options, headers });
  warnIfV1Token(response);
  return response;
}

/**
 * Returns a WebSocket URL with an auth token appended as a query param.
 * In LOCAL_MODE returns the plain ws:// URL without a token.
 */
export async function getAuthenticatedWsUrl(
  path: string,
  msalInstance: IPublicClientApplication,
  account: AccountInfo | null,
): Promise<string> {
  const base = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${path}`;
  if (LOCAL_MODE) return base;

  let token: string;
  try {
    const result = await msalInstance.acquireTokenSilent({ ...backendRequest, account: account! });
    token = result.accessToken;
  } catch (err) {
    if (err instanceof InteractionRequiredAuthError) {
      await msalInstance.acquireTokenRedirect(backendRequest);
      throw err;
    }
    throw err;
  }
  return `${base}?token=${encodeURIComponent(token)}`;
}
