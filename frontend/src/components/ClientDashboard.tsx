// frontend/src/components/ClientDashboard.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { VscAdd, VscFolder, VscArrowRight, VscWarning } from 'react-icons/vsc';
import { useApiFetch } from '@/hooks/useApiFetch';
import { useAuth } from '@/auth/AuthProvider';
import { useServiceHealth } from '@/hooks/useServiceHealth';

export function ClientDashboard() {
  const navigate = useNavigate();
  const { apiFetch } = useApiFetch();
  const { user } = useAuth();
  const initials = user?.name?.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase() ?? '?';
  const { backendOnline } = useServiceHealth();
  const [clients, setClients] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [showNewClient, setShowNewClient] = useState(false);
  const [newClientName, setNewClientName] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchClients();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchClients = async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await apiFetch('/api/clients');
      if (res.ok) {
        const data = await res.json();
        setClients(data.clients || []);
      } else {
        setFetchError(`Server returned ${res.status} — check backend logs`);
      }
    } catch (err) {
      console.error('Failed to fetch clients:', err);
      setFetchError('Could not reach the backend. Make sure the server is running on localhost:8000.');
    } finally {
      setLoading(false);
    }
  };

  const onboardClient = async () => {
    if (!newClientName.trim() || creating) return;
    setCreating(true);
    try {
      const res = await apiFetch('/api/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_name: newClientName.trim() }),
      });
      if (res.ok) {
        navigate(`/clients/${encodeURIComponent(newClientName.trim())}`);
      }
    } catch (err) {
      console.error('Failed to onboard client:', err);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary">
      <header className="border-b border-border-default bg-bg-secondary">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-start justify-between">
          <div>
            <h1 className="text-lg font-bold text-accent tracking-wide">CLIENT INTELLIGENCE AGENT</h1>
            <p className="text-sm text-text-secondary mt-1">Select a client to explore documents and insights</p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/profile')}
            title="View profile"
            aria-label="View profile"
            className="w-8 h-8 rounded-full bg-accent/20 text-accent text-sm font-bold flex items-center justify-center hover:bg-accent/30 transition-colors mt-1 flex-shrink-0"
          >
            {initials}
          </button>
        </div>
      </header>

      {backendOnline === false && (
        <div className="bg-yellow-500/10 border-b border-yellow-500/30 px-6 py-3 flex items-center gap-2 text-yellow-400 text-sm">
          <VscWarning size={16} className="flex-shrink-0" />
          <span>Backend is offline. Start the server at <code className="font-mono text-xs">localhost:8000</code>.</span>
        </div>
      )}

      {fetchError && (
        <div className="bg-red-500/10 border-b border-red-500/30 px-6 py-3 flex items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-2 text-red-400">
            <VscWarning size={16} className="flex-shrink-0" />
            <span>{fetchError}</span>
          </div>
          <button
            type="button"
            onClick={fetchClients}
            className="text-xs font-medium text-red-400 border border-red-500/40 rounded px-2 py-1 hover:bg-red-500/10 transition-colors flex-shrink-0"
          >
            Retry
          </button>
        </div>
      )}

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-wider">Your Clients</h2>
          <button
            type="button"
            onClick={() => setShowNewClient(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-accent text-bg-primary rounded hover:bg-accent-bright transition-colors"
            aria-label="Add a new client"
          >
            <VscAdd size={14} />
            Add Client
          </button>
        </div>

        {showNewClient && (
          <div className="mb-6 p-4 bg-bg-panel border border-border-default rounded-md">
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') onboardClient(); }}
                placeholder="Client name (e.g., Contoso)"
                autoFocus
                className="flex-1 px-3 py-2 text-sm bg-bg-secondary border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
              />
              <button
                type="button"
                onClick={onboardClient}
                disabled={!newClientName.trim() || creating}
                className="px-4 py-2 text-xs font-medium bg-accent text-bg-primary rounded hover:bg-accent-bright transition-colors disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => { setShowNewClient(false); setNewClientName(''); }}
                className="px-3 py-2 text-xs text-text-muted hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-text-muted text-sm">Loading clients...</div>
        ) : clients.length === 0 ? (
          <div className="text-center py-16">
            <VscFolder size={48} className="mx-auto text-text-muted mb-4" />
            <p className="text-text-secondary mb-2">No clients yet</p>
            <p className="text-xs text-text-muted mb-4">Add client folders to your OneDrive sync path, or create a new client above.</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {clients.map((client) => (
              <button
                key={client}
                type="button"
                onClick={() => navigate(`/clients/${encodeURIComponent(client)}`)}
                className="flex items-center justify-between p-4 bg-bg-panel border border-border-default rounded-md hover:border-accent/50 hover:bg-bg-hover transition-all group text-left"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-md bg-accent/10 flex items-center justify-center text-accent font-bold text-sm">
                    {client.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-text-primary">{client}</div>
                    <div className="text-xs text-text-muted">Click to open workspace</div>
                  </div>
                </div>
                <VscArrowRight size={16} className="text-text-muted group-hover:text-accent transition-colors" />
              </button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
