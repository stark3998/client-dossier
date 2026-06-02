// src/hooks/useMCPServers.ts
import { useState, useEffect, useCallback } from 'react';
import { useApiFetch } from '@/hooks/useApiFetch';
import type { MCPServerConfig } from '@/types';

export function useMCPServers() {
  const [servers, setServers] = useState<MCPServerConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const { apiFetch } = useApiFetch();

  const fetchServers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/mcp/servers');
      if (res.ok) {
        const data = await res.json();
        setServers(data.servers || []);
      }
    } catch (err) {
      console.error('Failed to fetch MCP servers:', err);
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => { fetchServers(); }, [fetchServers]);

  const addServer = async (config: Partial<MCPServerConfig>) => {
    const res = await apiFetch('/api/mcp/servers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (res.ok) { await fetchServers(); }
    return res.ok;
  };

  const removeServer = async (id: string) => {
    await apiFetch(`/api/mcp/servers/${id}`, { method: 'DELETE' });
    await fetchServers();
  };

  const testServer = async (id: string) => {
    const res = await apiFetch(`/api/mcp/servers/${id}/test`, { method: 'POST' });
    if (res.ok) return res.json();
    return { status: 'error', message: 'Request failed' };
  };

  return { servers, loading, addServer, removeServer, testServer, refresh: fetchServers };
}
