// frontend/src/components/settings/MCPServerPanel.tsx
import { useState } from 'react';
import { useMCPServers } from '@/hooks/useMCPServers';
import { useClientStore } from '@/stores/clientStore';
import { VscClose, VscAdd, VscPass, VscTrash } from 'react-icons/vsc';

export function MCPServerPanel() {
  const { showMCPPanel, setShowMCPPanel } = useClientStore();
  const { servers, addServer, removeServer, testServer, loading } = useMCPServers();
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [description, setDescription] = useState('');
  const [testing, setTesting] = useState<string | null>(null);

  if (!showMCPPanel) return null;

  const handleAdd = async () => {
    if (!name.trim() || !endpoint.trim()) return;
    await addServer({ name: name.trim(), endpoint: endpoint.trim(), description: description.trim() });
    setName('');
    setEndpoint('');
    setDescription('');
    setShowAdd(false);
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    await testServer(id);
    setTesting(null);
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={() => setShowMCPPanel(false)}
        role="presentation"
      />
      <div
        className="relative w-96 bg-bg-panel border-l border-border-default h-full overflow-y-auto"
        role="dialog"
        aria-label="MCP Servers"
      >
        <div className="flex items-center justify-between p-4 border-b border-border-default">
          <h2 className="text-sm font-semibold text-text-primary">MCP Servers</h2>
          <button
            type="button"
            onClick={() => setShowMCPPanel(false)}
            className="text-text-muted hover:text-text-primary"
            aria-label="Close panel"
          >
            <VscClose size={18} />
          </button>
        </div>

        <div className="p-4 space-y-3">
          <button
            type="button"
            onClick={() => setShowAdd(!showAdd)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-accent text-bg-primary rounded hover:bg-accent-bright transition-colors w-full justify-center"
          >
            <VscAdd size={14} /> Add MCP Server
          </button>

          {showAdd && (
            <div className="p-3 bg-bg-secondary rounded-md space-y-2">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Server name"
                className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <input
                type="text"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                placeholder="Endpoint URL"
                className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Description (optional)"
                className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleAdd}
                  className="flex-1 px-3 py-1.5 text-xs bg-accent text-bg-primary rounded hover:bg-accent-bright"
                >
                  Add
                </button>
                <button
                  type="button"
                  onClick={() => setShowAdd(false)}
                  className="px-3 py-1.5 text-xs text-text-muted hover:text-text-primary"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {loading ? (
            <div className="text-xs text-text-muted">Loading servers...</div>
          ) : servers.length === 0 ? (
            <div className="text-xs text-text-muted text-center py-4">No MCP servers configured</div>
          ) : (
            servers.map((s) => (
              <div key={s.id} className="p-3 bg-bg-secondary rounded-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      s.status === 'connected' ? 'bg-accent' :
                      s.status === 'error' ? 'bg-red-500' :
                      'bg-text-muted'
                    }`} />
                    <span className="text-xs font-medium text-text-primary">{s.name}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleTest(s.id)}
                      className="p-1 text-text-muted hover:text-accent-blue"
                      aria-label={`Test connection for ${s.name}`}
                    >
                      {testing === s.id ? <span className="text-[10px]">...</span> : <VscPass size={14} />}
                    </button>
                    <button
                      type="button"
                      onClick={() => removeServer(s.id)}
                      className="p-1 text-text-muted hover:text-red-400"
                      aria-label={`Remove ${s.name}`}
                    >
                      <VscTrash size={14} />
                    </button>
                  </div>
                </div>
                <div className="text-[10px] text-text-muted mt-1 truncate">{s.endpoint}</div>
                {s.description && <div className="text-[10px] text-text-secondary mt-0.5">{s.description}</div>}
                {s.last_error && <div className="text-[10px] text-red-400 mt-0.5">{s.last_error}</div>}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
