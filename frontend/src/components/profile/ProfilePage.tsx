// frontend/src/components/profile/ProfilePage.tsx
import { useState, useEffect } from 'react';
import { useMsal } from '@azure/msal-react';
import { InteractionRequiredAuthError } from '@azure/msal-browser';
import { useNavigate } from 'react-router-dom';
import { loginRequest, backendRequest } from '@/auth/msalConfig';
import { useTheme } from '@/contexts/ThemeContext';
import { BsSun, BsMoon } from 'react-icons/bs';

// ── JWT decode ────────────────────────────────────────────────────────────────
function decodeJwt(token: string): Record<string, unknown> {
  try {
    const [, payload] = token.split('.');
    const padded = payload.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(padded));
  } catch {
    return {};
  }
}

// ── TokenCard ─────────────────────────────────────────────────────────────────
const ID_TOKEN_HIGHLIGHTS = new Set(['aud', 'iss', 'iat', 'exp', 'name', 'preferred_username', 'oid', 'tid']);
const ACCESS_TOKEN_HIGHLIGHTS = new Set(['aud', 'iss', 'iat', 'exp', 'scp', 'roles', 'oid', 'tid']);

interface TokenData { raw: string; claims: Record<string, unknown>; }

function TokenCard({ title, tokenData, highlights, defaultExpanded = true }: {
  title: string;
  tokenData: TokenData | null;
  highlights: Set<string>;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);

  if (!tokenData) {
    return (
      <div className="bg-bg-panel border border-border-default rounded-md p-4">
        <div className="text-text-muted text-sm">{title} — loading...</div>
      </div>
    );
  }

  const { raw, claims } = tokenData;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(raw);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatValue = (key: string, val: unknown): string => {
    if ((key === 'exp' || key === 'iat') && typeof val === 'number') {
      return `${val} (${new Date(val * 1000).toLocaleString()})`;
    }
    if (Array.isArray(val)) return val.join(', ');
    return String(val);
  };

  return (
    <div className="bg-bg-panel border border-border-default rounded-md overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
        <span className="text-sm font-semibold text-text-primary">{title}</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="text-xs text-text-muted hover:text-text-primary px-2 py-1 rounded border border-border-default hover:border-accent/50 transition-colors"
          >
            {copied ? 'Copied!' : 'Copy raw'}
          </button>
          <button
            type="button"
            onClick={() => setExpanded(e => !e)}
            className="text-text-muted hover:text-text-primary text-xs"
            aria-label={expanded ? 'Collapse token claims' : 'Expand token claims'}
          >
            {expanded ? '▲' : '▼'}
          </button>
        </div>
      </div>

      <div className="px-4 py-2">
        <p className="font-mono text-xs text-text-muted break-all">
          {raw.slice(0, 20)}...{raw.slice(-20)}
        </p>
      </div>

      {expanded && (
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-bg-secondary">
              <th className="text-left px-4 py-2 text-text-muted font-medium w-40">Claim</th>
              <th className="text-left px-4 py-2 text-text-muted font-medium">Value</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(claims).map(([k, v], i) => (
              <tr key={k} className={i % 2 === 0 ? 'bg-bg-primary' : 'bg-bg-secondary'}>
                <td className={`px-4 py-1.5 font-mono ${highlights.has(k) ? 'text-accent' : 'text-text-secondary'}`}>
                  {k}
                </td>
                <td className="px-4 py-1.5 font-mono text-text-primary break-all">
                  {formatValue(k, v)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── ProfilePage ───────────────────────────────────────────────────────────────
export function ProfilePage() {
  const navigate = useNavigate();
  const { instance, accounts } = useMsal();
  const account = accounts[0] ?? null;
  const { isDark, toggleTheme } = useTheme();

  const [idToken, setIdToken] = useState<TokenData | null>(null);
  const [accessToken, setAccessToken] = useState<TokenData | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [customScopes, setCustomScopes] = useState('');
  const [customToken, setCustomToken] = useState<TokenData | null>(null);
  const [customError, setCustomError] = useState<string | null>(null);
  const [acquiringCustom, setAcquiringCustom] = useState(false);

  const loadTokens = async (forceRefresh = false) => {
    if (!account) return;
    try {
      const [idRes, accessRes] = await Promise.allSettled([
        instance.acquireTokenSilent({ ...loginRequest, account, forceRefresh }),
        instance.acquireTokenSilent({ ...backendRequest, account, forceRefresh }),
      ]);
      if (idRes.status === 'fulfilled' && idRes.value.idToken) {
        setIdToken({ raw: idRes.value.idToken, claims: decodeJwt(idRes.value.idToken) });
      }
      if (accessRes.status === 'fulfilled') {
        setAccessToken({ raw: accessRes.value.accessToken, claims: decodeJwt(accessRes.value.accessToken) });
      }
    } catch {
      // non-fatal — tokens may not be available immediately
    }
  };

  useEffect(() => {
    loadTokens();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadTokens(true);
    setIsRefreshing(false);
  };

  const handleAcquireCustom = async () => {
    if (!account || !customScopes.trim()) return;
    setAcquiringCustom(true);
    setCustomError(null);
    const scopes = customScopes.split(',').map(s => s.trim()).filter(Boolean);
    try {
      let result;
      try {
        result = await instance.acquireTokenSilent({ scopes, account });
      } catch (err) {
        if (err instanceof InteractionRequiredAuthError) {
          result = await instance.acquireTokenPopup({ scopes, account });
        } else throw err;
      }
      setCustomToken({ raw: result.accessToken, claims: decodeJwt(result.accessToken) });
    } catch (err) {
      setCustomError(err instanceof Error ? err.message : String(err));
    } finally {
      setAcquiringCustom(false);
    }
  };

  const idClaims = idToken?.claims ?? {};

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Header */}
      <header className="h-12 border-b border-border-default flex items-center px-4 gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="text-text-muted hover:text-text-primary text-sm flex items-center gap-1 transition-colors"
        >
          &larr; Back
        </button>
        <span className="text-text-muted">/</span>
        <span className="text-text-primary text-sm font-medium tracking-widest uppercase">Profile</span>
        <div className="ml-auto flex items-center gap-3">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="text-xs px-3 py-1.5 bg-bg-secondary border border-border-default rounded hover:border-accent/50 text-text-secondary hover:text-text-primary transition-colors disabled:opacity-50"
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh tokens'}
          </button>
          <button
            type="button"
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="text-text-muted hover:text-text-primary transition-colors p-1 rounded"
          >
            {isDark ? <BsSun size={14} /> : <BsMoon size={14} />}
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        {/* User Card */}
        <div className="bg-bg-panel border border-border-default rounded-md p-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-accent/20 text-accent text-lg font-bold flex items-center justify-center flex-shrink-0">
              {account?.name?.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase() ?? '?'}
            </div>
            <div className="min-w-0">
              <div className="text-text-primary font-semibold">{account?.name ?? '—'}</div>
              <div className="text-text-muted text-sm">{account?.username ?? '—'}</div>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
            {[
              ['Object ID', String(idClaims.oid ?? '—')],
              ['Tenant ID', String(idClaims.tid ?? '—')],
              ['Account type', idClaims.acct === 0 ? 'Work / School' : idClaims.acct === 1 ? 'Personal' : '—'],
              ['Auth time', idClaims.auth_time ? new Date(Number(idClaims.auth_time) * 1000).toLocaleString() : '—'],
            ].map(([label, value]) => (
              <div key={label} className="bg-bg-secondary rounded px-3 py-2">
                <div className="text-text-muted mb-0.5">{label}</div>
                <div className="font-mono text-text-primary break-all">{value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* ID Token */}
        <div>
          <h2 className="text-xs uppercase tracking-widest text-text-muted mb-2">ID Token</h2>
          <TokenCard
            title="ID Token"
            tokenData={idToken}
            highlights={ID_TOKEN_HIGHLIGHTS}
            defaultExpanded={true}
          />
        </div>

        {/* Access Token */}
        <div>
          <h2 className="text-xs uppercase tracking-widest text-text-muted mb-2">Access Token (Backend API)</h2>
          <TokenCard
            title="Access Token"
            tokenData={accessToken}
            highlights={ACCESS_TOKEN_HIGHLIGHTS}
            defaultExpanded={false}
          />
        </div>

        {/* Scope Selector */}
        <div className="bg-bg-panel border border-border-default rounded-md p-5">
          <h2 className="text-sm font-semibold text-text-primary mb-3">Acquire Custom Scopes</h2>
          <div className="flex gap-2">
            <input
              type="text"
              value={customScopes}
              onChange={e => setCustomScopes(e.target.value)}
              placeholder="User.Read, Mail.Read, ..."
              className="flex-1 bg-bg-secondary border border-border-default rounded px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent/50 focus:ring-2 focus:ring-accent/20"
              onKeyDown={e => e.key === 'Enter' && handleAcquireCustom()}
            />
            <button
              type="button"
              onClick={handleAcquireCustom}
              disabled={acquiringCustom || !customScopes.trim()}
              className="px-4 py-2 text-sm bg-accent text-bg-primary font-medium rounded hover:bg-accent-bright transition-colors disabled:opacity-50"
            >
              {acquiringCustom ? 'Acquiring...' : 'Acquire'}
            </button>
          </div>
          {customError && (
            <p className="mt-2 text-xs text-red-400">{customError}</p>
          )}
        </div>

        {/* Custom Token Result */}
        {customToken && (
          <div>
            <h2 className="text-xs uppercase tracking-widest text-text-muted mb-2">Custom Scope Token</h2>
            <TokenCard
              title={`Token for: ${customScopes}`}
              tokenData={customToken}
              highlights={new Set(['aud', 'iss', 'scp', 'roles', 'exp'])}
              defaultExpanded={true}
            />
          </div>
        )}
      </main>
    </div>
  );
}
