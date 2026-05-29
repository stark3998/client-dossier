// frontend/src/components/tools/ToolBrowser.tsx
import { useState } from 'react';
import { useTools } from '@/hooks/useTools';
import { VscSymbolMethod, VscAdd, VscPlay } from 'react-icons/vsc';
import type { Tool } from '@/types';

export function ToolBrowser() {
  const { tools, loading, invokeTool, createCustomTool } = useTools();
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [args, setArgs] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPrompt, setNewPrompt] = useState('');

  const handleInvoke = async () => {
    if (!selectedTool) return;
    setRunning(true);
    setResult(null);
    const res = await invokeTool(selectedTool.plugin, selectedTool.name, args);
    setResult(res?.result || 'No result');
    setRunning(false);
  };

  const handleCreate = async () => {
    if (!newName.trim() || !newPrompt.trim()) return;
    await createCustomTool({
      name: newName.trim(),
      description: newDesc.trim(),
      prompt_template: newPrompt.trim(),
    });
    setNewName('');
    setNewDesc('');
    setNewPrompt('');
    setShowCreate(false);
  };

  const grouped = tools.reduce<Record<string, Tool[]>>((acc, t) => {
    const cat = t.is_custom ? 'Custom' : t.plugin;
    (acc[cat] = acc[cat] || []).push(t);
    return acc;
  }, {});

  if (selectedTool) {
    return (
      <div className="p-3 space-y-3">
        <button
          type="button"
          onClick={() => { setSelectedTool(null); setResult(null); }}
          className="text-xs text-accent-blue hover:underline"
        >
          Back to tools
        </button>
        <div>
          <div className="text-sm font-medium text-text-primary">{selectedTool.name}</div>
          <div className="text-xs text-text-secondary mt-0.5">{selectedTool.description}</div>
          <div className="text-[10px] text-text-muted mt-0.5">{selectedTool.plugin}</div>
        </div>
        {selectedTool.parameters.length > 0 && (
          <div className="space-y-2">
            {selectedTool.parameters.map((p) => (
              <div key={p.name}>
                <label className="text-[10px] text-text-muted uppercase">
                  {p.name}{p.required ? ' *' : ''}
                </label>
                <input
                  type="text"
                  value={args[p.name] || ''}
                  onChange={(e) => setArgs({ ...args, [p.name]: e.target.value })}
                  placeholder={p.description || p.name}
                  className="w-full px-2 py-1 text-xs bg-bg-panel border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent mt-0.5"
                />
              </div>
            ))}
          </div>
        )}
        <button
          type="button"
          onClick={handleInvoke}
          disabled={running}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-accent text-bg-primary rounded hover:bg-accent-bright transition-colors disabled:opacity-50 w-full justify-center"
        >
          <VscPlay size={12} /> {running ? 'Running...' : 'Execute'}
        </button>
        {result && (
          <div className="p-2 bg-bg-secondary rounded text-xs text-text-secondary font-mono whitespace-pre-wrap max-h-48 overflow-y-auto">
            {result}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-3 space-y-3 overflow-y-auto flex-1">
        <button
          type="button"
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-accent/10 text-accent rounded hover:bg-accent/20 transition-colors w-full justify-center"
        >
          <VscAdd size={14} /> Create Custom Tool
        </button>

        {showCreate && (
          <div className="p-3 bg-bg-secondary rounded-md space-y-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Tool name"
              className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <input
              type="text"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder="Description"
              className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <textarea
              value={newPrompt}
              onChange={(e) => setNewPrompt(e.target.value)}
              placeholder="Prompt template (use {{$input}} for variables)"
              rows={4}
              className="w-full px-2 py-1.5 text-xs bg-bg-panel border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent resize-none font-mono"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleCreate}
                className="flex-1 px-3 py-1.5 text-xs bg-accent text-bg-primary rounded hover:bg-accent-bright"
              >
                Create
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="px-3 py-1.5 text-xs text-text-muted hover:text-text-primary"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-xs text-text-muted">Loading tools...</div>
        ) : Object.keys(grouped).length === 0 ? (
          <div className="text-xs text-text-muted text-center py-4">No tools available</div>
        ) : (
          Object.entries(grouped).map(([category, categoryTools]) => (
            <div key={category}>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">{category}</div>
              <div className="space-y-1">
                {categoryTools.map((t) => (
                  <button
                    key={`${t.plugin}-${t.name}`}
                    type="button"
                    onClick={() => { setSelectedTool(t); setArgs({}); setResult(null); }}
                    className="flex items-center gap-2 w-full p-2 text-left rounded hover:bg-bg-hover transition-colors"
                  >
                    <VscSymbolMethod size={14} className="text-accent-blue shrink-0" />
                    <div className="min-w-0">
                      <div className="text-xs text-text-primary truncate">{t.name}</div>
                      <div className="text-[10px] text-text-muted truncate">{t.description}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
