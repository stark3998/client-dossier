// frontend/src/components/settings/MCPServerPanel.tsx
import { useState } from 'react';
import { useMCPServers } from '@/hooks/useMCPServers';
import { useClientStore } from '@/stores/clientStore';
import { VscClose, VscAdd, VscPass, VscTrash, VscPackage } from 'react-icons/vsc';
import { MCP_PRESETS, type MCPPreset } from '@/data/mcpPresets';

export function MCPServerPanel() {
  const { showMCPPanel, setShowMCPPanel } = useClientStore();
  const { servers, addServer, removeServer, testServer, loading } = useMCPServers();
  const [showAdd, setShowAdd] = useState(false);
  const [showPresets, setShowPresets] = useState(false);
  const [name, setName] = useState('');
  const [endpoint, setEndpoint] = useState('');
  const [description, setDescription] = useState('');
  const [protocol, setProtocol] = useState<'rest' | 'sse'>('rest');
  const [authType, setAuthType] = useState<'none' | 'api_key' | 'bearer'>('none');
  const [authKey, setAuthKey] = useState('');
  const [authPlaceholder, setAuthPlaceholder] = useState('API Key');
  const [testing, setTesting] = useState<string | null>(null);

  if (!showMCPPanel) return null;

  const applyPreset = (preset: MCPPreset) => {
    setName(preset.name);
    setEndpoint(preset.endpoint);
    setDescription(preset.description);
    setProtocol(preset.protocol);
    setAuthType(preset.auth_type);
    setAuthPlaceholder(preset.auth_placeholder ?? 'API Key');
    setAuthKey('');
    setShowPresets(false);
    setShowAdd(true);
  };

  const handleAdd = async () => {
    if (!name.trim() || !endpoint.trim()) return;
    const authConfig: Record<string, string> = {};
    if (authType === 'api_key') authConfig['api_key'] = authKey;
    if (authType === 'bearer') authConfig['token'] = authKey;

    await addServer({
      name: name.trim(),
      endpoint: endpoint.trim(),
      description: description.trim(),
      protocol,
      auth_type: authType,
      auth_config: authConfig,
    });
    setName(''); setEndpoint(''); setDescription('');
    setProtocol('rest'); setAuthType('none'); setAuthKey('');
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
          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => { setShowAdd(!showAdd); setShowPresets(false); }}
              className="flex-1 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-accent text-bg-primary rounded hover:bg-accent-bright transition-colors justify-center"
            >
              <VscAdd size={14} /> Custom
            </button>
            <button
              type="button"
              onClick={() => { setShowPresets(!showPresets); setShowAdd(false); }}
              className="flex-1 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-bg-secondary text-text-secondary border border-border-default rounded hover:text-text-primary transition-colors justify-center"
            >
              <VscPackage size={14} /> Presets
            </button>
          </div>

          {/* Presets grid */}
          {showPresets && (
            <div className="space-y-2">
              <p className="text-[10px] text-text-muted uppercase tracking-wider">Select a preset to pre-fill</p>
              {MCP_PRESETS.map((preset) => (
                <button
                  key={preset.name}
                  type="button"
                  onClick={() => applyPreset(preset)}
                  className="w-full text-left p-3 bg-bg-secondary rounded-md hover:bg-bg-hover border border-transparent hover:border-accent/30 transition-colors"
                >
                  <div className="text-xs font-medium text-text-primary">{preset.name}</div>
                  <div className="text-[10px] text-text-muted mt-0.5 line-clamp-2">{preset.description}</div>
                  <div className="flex gap-1 mt-1.5 flex-wrap">
                    {preset.capabilities.map((cap) => (
                      <span key={cap} className="px-1.5 py-0.5 text-[9px] bg-accent/10 text-accent rounded">
                        {cap}
                      </span>
                    ))}
                    <span className="px-1.5 py-0.5 text-[9px] bg-bg-panel text-text-muted rounded border border-border-default">
                      {preset.protocol.toUpperCase()}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Add / edit form */}
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
                <div className="flex-1">
                  <label className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">Protocol</label>
                  <select
                    value={protocol}
                    onChange={(e) => setProtocol(e.target.value as 'rest' | 'sse')}
                    aria-label="Protocol"
                    className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
                  >
                    <option value="rest">REST (custom)</option>
                    <option value="sse">SSE (standard MCP)</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-[10px] text-text-muted uppercase tracking-wider block mb-1">Auth</label>
                  <select
                    value={authType}
                    onChange={(e) => setAuthType(e.target.value as 'none' | 'api_key' | 'bearer')}
                    aria-label="Auth type"
                    className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
                  >
                    <option value="none">None</option>
                    <option value="api_key">API Key</option>
                    <option value="bearer">Bearer</option>
                  </select>
                </div>
              </div>
              {authType !== 'none' && (
                <input
                  type="password"
                  value={authKey}
                  onChange={(e) => setAuthKey(e.target.value)}
                  placeholder={authPlaceholder}
                  className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
                />
              )}
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

          {/* Server list */}
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
                    {s.protocol && s.protocol !== 'rest' && (
                      <span className="text-[9px] px-1 py-0.5 bg-accent/10 text-accent rounded">{s.protocol.toUpperCase()}</span>
                    )}
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
