// src/hooks/useTools.ts
import { useState, useEffect, useCallback } from 'react';
import type { Tool, ToolInvocationResult } from '@/types';

export function useTools() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTools = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/tools');
      if (res.ok) {
        const data = await res.json();
        setTools(data.tools || []);
      }
    } catch (err) {
      console.error('Failed to fetch tools:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchTools(); }, [fetchTools]);

  const invokeTool = async (plugin: string, fn: string, args: Record<string, string>): Promise<ToolInvocationResult | null> => {
    try {
      const res = await fetch('/api/tools/invoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plugin, function: fn, arguments: args }),
      });
      if (res.ok) return res.json();
    } catch (err) {
      console.error('Tool invocation failed:', err);
    }
    return null;
  };

  const createCustomTool = async (tool: { name: string; description: string; prompt_template: string }) => {
    const res = await fetch('/api/tools/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tool),
    });
    if (res.ok) { await fetchTools(); }
    return res.ok;
  };

  const deleteCustomTool = async (id: string) => {
    await fetch(`/api/tools/custom/${id}`, { method: 'DELETE' });
    await fetchTools();
  };

  return { tools, loading, invokeTool, createCustomTool, deleteCustomTool, refresh: fetchTools };
}
