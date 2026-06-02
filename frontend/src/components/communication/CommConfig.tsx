// frontend/src/components/communication/CommConfig.tsx
import { useEffect, useState } from 'react';
import { VscAdd, VscClose, VscLoading, VscSave } from 'react-icons/vsc';
import { useCommConfig } from '../../hooks/useCommunication';
import type { CommunicationConfig, OutlookAccount } from '../../types';

interface Props {
  clientName: string;
}

function TagInput({ tags, onChange, placeholder }: { tags: string[]; onChange: (t: string[]) => void; placeholder: string }) {
  const [input, setInput] = useState('');
  function add() {
    const v = input.trim();
    if (v && !tags.includes(v)) onChange([...tags, v]);
    setInput('');
  }
  return (
    <div>
      <div className="flex flex-wrap gap-1 mb-1.5">
        {tags.map((t) => (
          <span key={t} className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">
            {t}
            <button type="button" onClick={() => onChange(tags.filter((x) => x !== t))} aria-label={`Remove ${t}`}>
              <VscClose size={9} aria-hidden="true" />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-1">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
          placeholder={placeholder}
          className="flex-1 px-2 py-1 text-xs bg-bg-secondary border border-border-default rounded text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent"
          aria-label={placeholder}
        />
        <button type="button" onClick={add} className="px-2 py-1 text-xs rounded bg-bg-secondary border border-border-default text-text-muted hover:text-text-primary" aria-label="Add">
          <VscAdd size={11} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

function AccountEditor({
  account,
  availableFolders,
  onLoadFolders,
  onChange,
  onRemove,
}: {
  account: OutlookAccount;
  availableFolders: string[];
  onLoadFolders: () => void;
  onChange: (a: OutlookAccount) => void;
  onRemove: () => void;
}) {
  return (
    <div className="p-3 bg-bg-secondary border border-border-default rounded space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-primary">{account.display_name}</span>
        <button type="button" onClick={onRemove} className="text-text-muted hover:text-red-400" aria-label="Remove account">
          <VscClose size={12} aria-hidden="true" />
        </button>
      </div>
      <div>
        <div className="text-[10px] text-text-muted mb-1">Folders to scan</div>
        <div className="flex flex-wrap gap-1 mb-1">
          {account.folders.map((f) => (
            <span key={f} className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-bg-panel text-text-secondary">
              {f}
              <button type="button" onClick={() => onChange({ ...account, folders: account.folders.filter((x) => x !== f) })} aria-label={`Remove ${f}`}>
                <VscClose size={9} aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-1">
          <select
            onChange={(e) => {
              const val = e.target.value;
              if (val && !account.folders.includes(val)) {
                onChange({ ...account, folders: [...account.folders, val] });
              }
              e.target.value = '';
            }}
            onClick={availableFolders.length === 0 ? onLoadFolders : undefined}
            className="flex-1 px-2 py-1 text-xs bg-bg-secondary border border-border-default rounded text-text-secondary focus:outline-none"
            aria-label="Add folder"
          >
            <option value="">Add folder…</option>
            {availableFolders.map((f) => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      </div>
    </div>
  );
}

const DEFAULT_CONFIG: CommunicationConfig = {
  id: '',
  client_name: '',
  domains: [],
  keywords: [],
  accounts: [],
  contacts: [],
  scan_sent: true,
  auto_draft: true,
  scan_interval_minutes: 15,
};

export function CommConfig({ clientName }: Props) {
  const { config, accounts: outlookAccounts, loading, saveConfig, fetchFolders } = useCommConfig(clientName);
  const [form, setForm] = useState<CommunicationConfig>(DEFAULT_CONFIG);
  const [folderCache, setFolderCache] = useState<Record<string, string[]>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (config) {
      setForm(config);
    } else {
      setForm({ ...DEFAULT_CONFIG, id: clientName.toLowerCase().replace(/ /g, '-'), client_name: clientName });
    }
  }, [config, clientName]);

  function setField<K extends keyof CommunicationConfig>(key: K, value: CommunicationConfig[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function loadFolders(accountName: string) {
    if (folderCache[accountName]) return;
    const folders = await fetchFolders(accountName);
    setFolderCache((c) => ({ ...c, [accountName]: folders }));
  }

  function addAccount(name: string) {
    if (!name || form.accounts.some((a) => a.display_name === name)) return;
    setField('accounts', [...form.accounts, { display_name: name, folders: ['Inbox'] }]);
  }

  function updateAccount(idx: number, a: OutlookAccount) {
    const next = [...form.accounts];
    next[idx] = a;
    setField('accounts', next);
  }

  function removeAccount(idx: number) {
    setField('accounts', form.accounts.filter((_, i) => i !== idx));
  }

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await saveConfig(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="p-6 text-text-muted text-sm">Loading…</div>;

  return (
    <div className="p-4 space-y-5 max-w-xl">
      <div className="space-y-1.5">
        <label className="text-[10px] text-text-muted uppercase tracking-wide">Email Domains</label>
        <p className="text-[10px] text-text-muted">Emails to/from these domains will be attributed to this client.</p>
        <TagInput tags={form.domains} onChange={(t) => setField('domains', t)} placeholder="@acme.com" />
      </div>

      <div className="space-y-1.5">
        <label className="text-[10px] text-text-muted uppercase tracking-wide">Keywords</label>
        <p className="text-[10px] text-text-muted">Match emails containing these words in subject or body.</p>
        <TagInput tags={form.keywords} onChange={(t) => setField('keywords', t)} placeholder="Project Phoenix" />
      </div>

      <div className="space-y-1.5">
        <label className="text-[10px] text-text-muted uppercase tracking-wide">Specific Contacts</label>
        <p className="text-[10px] text-text-muted">Always attribute emails to/from these addresses to this client.</p>
        <TagInput tags={form.contacts} onChange={(t) => setField('contacts', t)} placeholder="john.smith@acme.com" />
      </div>

      <div className="space-y-1.5">
        <label className="text-[10px] text-text-muted uppercase tracking-wide">Outlook Accounts & Folders</label>
        <div className="space-y-2">
          {form.accounts.map((a, i) => (
            <AccountEditor
              key={a.display_name}
              account={a}
              availableFolders={folderCache[a.display_name] ?? []}
              onLoadFolders={() => loadFolders(a.display_name)}
              onChange={(updated) => updateAccount(i, updated)}
              onRemove={() => removeAccount(i)}
            />
          ))}
          {outlookAccounts.length > 0 && (
            <select
              onChange={(e) => { addAccount(e.target.value); e.target.value = ''; }}
              className="w-full px-2 py-1 text-xs bg-bg-secondary border border-border-default rounded text-text-secondary focus:outline-none"
              aria-label="Add Outlook account"
            >
              <option value="">Add Outlook account…</option>
              {outlookAccounts
                .filter((a) => !form.accounts.some((fa) => fa.display_name === a))
                .map((a) => <option key={a} value={a}>{a}</option>)
              }
            </select>
          )}
          {outlookAccounts.length === 0 && (
            <p className="text-[10px] text-text-muted">No Outlook accounts detected (Outlook may not be running).</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={form.scan_sent}
            onChange={(e) => setField('scan_sent', e.target.checked)}
            className="accent-accent"
          />
          <span className="text-xs text-text-primary">Scan Sent Items</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={form.auto_draft}
            onChange={(e) => setField('auto_draft', e.target.checked)}
            className="accent-accent"
          />
          <span className="text-xs text-text-primary">Auto-generate draft replies</span>
        </label>
      </div>

      <div className="space-y-1.5">
        <label className="text-[10px] text-text-muted uppercase tracking-wide" htmlFor="scan-interval">Scan interval (minutes)</label>
        <input
          id="scan-interval"
          type="number"
          min={5}
          max={1440}
          value={form.scan_interval_minutes}
          onChange={(e) => setField('scan_interval_minutes', Number(e.target.value))}
          className="w-24 px-2 py-1 text-xs bg-bg-secondary border border-border-default rounded text-text-primary focus:outline-none focus:border-accent"
        />
      </div>

      <button
        type="button"
        onClick={handleSave}
        disabled={saving}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-accent text-white hover:bg-accent/90 disabled:opacity-50"
      >
        {saving ? <VscLoading size={11} className="animate-spin" aria-hidden="true" /> : <VscSave size={11} aria-hidden="true" />}
        {saved ? 'Saved!' : 'Save Configuration'}
      </button>
    </div>
  );
}
