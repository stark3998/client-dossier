// frontend/src/components/settings/ClientSettings.tsx
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { VscArrowLeft, VscSave } from 'react-icons/vsc';
import { useInsights } from '@/hooks/useInsights';
import { useClientStore } from '@/stores/clientStore';
import { CommConfig } from '@/components/communication/CommConfig';
import type { ClientMemory, EngagementDefaults, McpServerStatus } from '@/types';

type Tab = 'profile' | 'communications' | 'engagement' | 'mcp';

const TABS: { id: Tab; label: string }[] = [
  { id: 'profile', label: 'Client Profile' },
  { id: 'communications', label: 'Communications' },
  { id: 'engagement', label: 'Engagement Defaults' },
  { id: 'mcp', label: 'MCP / Tools' },
];

const inputCls =
  'w-full px-3 py-1.5 text-xs bg-bg-secondary border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent';
const textareaCls = `${inputCls} resize-none`;
const saveBtnCls =
  'flex items-center gap-2 px-3 py-1.5 text-xs rounded bg-accent text-bg-primary hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

function FormField({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-1.5">
        <label className="text-xs font-medium text-text-secondary">{label}</label>
        {hint && <span className="text-[10px] text-text-muted">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

function ProfileTab({
  memory,
  updateMemory,
}: {
  memory: ClientMemory | null;
  updateMemory: (u: Partial<ClientMemory>) => Promise<void>;
}) {
  const [industry, setIndustry] = useState('');
  const [priorities, setPriorities] = useState('');
  const [painPoints, setPainPoints] = useState('');
  const [financials, setFinancials] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!memory) return;
    setIndustry(memory.industry ?? '');
    setPriorities((memory.strategic_priorities ?? []).join('\n'));
    setPainPoints((memory.pain_points ?? []).join('\n'));
    setFinancials(memory.financials_summary ?? '');
  }, [memory]);

  async function handleSave() {
    setSaving(true);
    try {
      await updateMemory({
        industry: industry || undefined,
        strategic_priorities: priorities
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        pain_points: painPoints
          .split('\n')
          .map((s) => s.trim())
          .filter(Boolean),
        financials_summary: financials || undefined,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-5">
      <h2 className="text-sm font-semibold text-text-primary">Client Profile</h2>

      <FormField label="Industry">
        <input
          type="text"
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          className={inputCls}
          placeholder="e.g. Financial Services"
        />
      </FormField>

      <FormField label="Strategic Priorities" hint="One per line">
        <textarea
          value={priorities}
          onChange={(e) => setPriorities(e.target.value)}
          rows={5}
          className={textareaCls}
          placeholder={'Reduce operational costs\nExpand into APAC\nModernise core infrastructure'}
        />
      </FormField>

      <FormField label="Pain Points" hint="One per line">
        <textarea
          value={painPoints}
          onChange={(e) => setPainPoints(e.target.value)}
          rows={4}
          className={textareaCls}
          placeholder={'Legacy systems\nTalent retention\nRegulatory compliance'}
        />
      </FormField>

      <FormField label="Financials Summary">
        <textarea
          value={financials}
          onChange={(e) => setFinancials(e.target.value)}
          rows={3}
          className={textareaCls}
          placeholder="Revenue, key financial metrics, budget context…"
        />
      </FormField>

      <button type="button" onClick={handleSave} disabled={saving} className={saveBtnCls}>
        <VscSave size={13} />
        {saving ? 'Saving…' : saved ? 'Saved!' : 'Save Profile'}
      </button>
    </div>
  );
}

interface EngagementDefaults {
  default_phase?: string;
  default_type?: string;
  billing_code?: string;
}

function EngagementDefaultsTab({
  memory,
  updateMemory,
}: {
  memory: ClientMemory | null;
  updateMemory: (u: Partial<ClientMemory>) => Promise<void>;
}) {
  const defaults: EngagementDefaults = (memory as (ClientMemory & { engagement_defaults?: EngagementDefaults }) | null)?.engagement_defaults ?? {};
  const [phase, setPhase] = useState(defaults.default_phase ?? 'discovery');
  const [type, setType] = useState(defaults.default_type ?? '');
  const [billing, setBilling] = useState(defaults.billing_code ?? '');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const d: EngagementDefaults = (memory as (ClientMemory & { engagement_defaults?: EngagementDefaults }) | null)?.engagement_defaults ?? {};
    setPhase(d.default_phase ?? 'discovery');
    setType(d.default_type ?? '');
    setBilling(d.billing_code ?? '');
  }, [memory]);

  async function handleSave() {
    setSaving(true);
    try {
      await updateMemory({
        engagement_defaults: { default_phase: phase, default_type: type, billing_code: billing },
      } as Partial<ClientMemory>);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-5">
      <h2 className="text-sm font-semibold text-text-primary">Engagement Defaults</h2>
      <p className="text-xs text-text-secondary">
        These defaults pre-populate new engagements created for this client.
      </p>

      <FormField label="Default Phase">
        <select
          value={phase}
          onChange={(e) => setPhase(e.target.value)}
          className={inputCls}
          aria-label="Default Phase"
        >
          {['discovery', 'design', 'execute', 'deliver', 'sustain'].map((p) => (
            <option key={p} value={p}>
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </option>
          ))}
        </select>
      </FormField>

      <FormField label="Default Engagement Type">
        <input
          type="text"
          value={type}
          onChange={(e) => setType(e.target.value)}
          className={inputCls}
          placeholder="e.g. Advisory, Implementation, Audit"
        />
      </FormField>

      <FormField label="Default Billing Code">
        <input
          type="text"
          value={billing}
          onChange={(e) => setBilling(e.target.value)}
          className={inputCls}
          placeholder="e.g. PRJ-2024-001"
        />
      </FormField>

      <button type="button" onClick={handleSave} disabled={saving} className={saveBtnCls}>
        <VscSave size={13} />
        {saving ? 'Saving…' : saved ? 'Saved!' : 'Save Defaults'}
      </button>
    </div>
  );
}

function MCPTab({
  mcpServers,
  onOpenPanel,
}: {
  mcpServers: McpServerStatus[];
  onOpenPanel: () => void;
}) {
  return (
    <div className="max-w-2xl space-y-4">
      <h2 className="text-sm font-semibold text-text-primary">MCP / Tools</h2>
      <p className="text-xs text-text-secondary">
        MCP server configuration is shared across all clients. Use the panel below to add or remove
        servers.
      </p>

      <div className="space-y-1.5">
        <div className="flex items-center gap-2 px-3 py-2 rounded bg-accent-blue/10 border border-accent-blue/20">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-blue shrink-0" />
          <span className="text-xs text-text-primary">Built-in MCP Server</span>
          <span className="ml-auto text-[10px] text-accent-blue">Connected</span>
        </div>
        {mcpServers.map((s) => (
          <div
            key={s.name}
            className="flex items-center gap-2 px-3 py-2 rounded bg-bg-secondary border border-border-default"
          >
            <span
              className={`w-1.5 h-1.5 rounded-full shrink-0 ${s.connected ? 'bg-accent' : 'bg-text-muted'}`}
            />
            <span className="text-xs text-text-primary">{s.name}</span>
            <span
              className={`ml-auto text-[10px] ${s.connected ? 'text-accent' : 'text-text-muted'}`}
            >
              {s.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        ))}
        {mcpServers.length === 0 && (
          <p className="text-xs text-text-muted px-1">No custom MCP servers configured.</p>
        )}
      </div>

      <button
        type="button"
        onClick={onOpenPanel}
        className="flex items-center gap-2 px-3 py-1.5 text-xs rounded bg-bg-secondary border border-border-default hover:border-accent/30 text-text-secondary hover:text-text-primary transition-colors"
      >
        Manage MCP Servers
      </button>
    </div>
  );
}

export function ClientSettings() {
  const { clientName = '' } = useParams<{ clientName: string }>();
  const navigate = useNavigate();
  const decodedName = decodeURIComponent(clientName);
  const [activeTab, setActiveTab] = useState<Tab>('profile');
  const { memory, updateMemory } = useInsights();
  const { setShowMCPPanel, mcpServers } = useClientStore();

  return (
    <div className="min-h-screen h-screen bg-bg-primary flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-4 h-12 bg-bg-secondary border-b border-border-default shrink-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/clients/${encodeURIComponent(decodedName)}`)}
            className="text-text-muted hover:text-text-primary transition-colors"
            aria-label="Back to workspace"
          >
            <VscArrowLeft size={16} />
          </button>
          <span className="text-sm font-bold text-accent tracking-wide">
            {decodedName} — Settings
          </span>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex border-b border-border-default bg-bg-secondary shrink-0 px-4">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActiveTab(t.id)}
            className={`px-4 py-2.5 text-xs font-medium transition-colors border-b-2 -mb-px ${
              activeTab === t.id
                ? 'border-accent text-accent'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'profile' && (
          <ProfileTab memory={memory} updateMemory={updateMemory} />
        )}
        {activeTab === 'communications' && <CommConfig clientName={decodedName} />}
        {activeTab === 'engagement' && (
          <EngagementDefaultsTab memory={memory} updateMemory={updateMemory} />
        )}
        {activeTab === 'mcp' && (
          <MCPTab mcpServers={mcpServers} onOpenPanel={() => setShowMCPPanel(true)} />
        )}
      </div>
    </div>
  );
}
