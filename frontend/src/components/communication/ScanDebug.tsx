// frontend/src/components/communication/ScanDebug.tsx
import { useState } from 'react';
import { VscBeaker, VscCheck, VscClose, VscWarning, VscChevronDown, VscChevronRight } from 'react-icons/vsc';
import { useApiFetch } from '@/hooks/useApiFetch';

// ── Types matching the backend /debug response ────────────────────────────────

interface FolderResult {
  folder: string;
  found_in_outlook: boolean;
  emails_fetched: number;
  emails_attributed: number;
  emails_rejected: number;
  sample: { subject: string; sender: string; received_at: string; match: string }[];
  rejection_reasons: { subject: string; sender: string; reason: string }[];
  error?: string;
}

interface AccountResult {
  account: string;
  outlook_folders_available: string[];
  folders_scanned: FolderResult[];
}

interface DebugReport {
  client_name: string;
  client_id: string;
  outlook: {
    status: 'ok' | 'unavailable' | 'error';
    accounts?: string[];
    error?: string;
  };
  config: {
    status: 'ok' | 'not_found' | 'error' | 'scanner_not_initialised';
    domains?: string[];
    keywords?: string[];
    contacts?: string[];
    accounts?: { display_name: string; folders: string[] }[];
    scan_sent?: boolean;
    auto_draft?: boolean;
    hint?: string;
    error?: string;
  };
  scan_preview: AccountResult[];
  errors: string[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: 'ok' | 'warn' | 'error' | 'info' }) {
  const map = {
    ok:    'bg-green-500/10 text-green-400 border-green-500/20',
    warn:  'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
    error: 'bg-red-500/10 text-red-400 border-red-500/20',
    info:  'bg-accent/10 text-accent border-accent/20',
  };
  const icon = {
    ok:    <VscCheck size={10} />,
    warn:  <VscWarning size={10} />,
    error: <VscClose size={10} />,
    info:  <VscBeaker size={10} />,
  };
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-medium ${map[status]}`}>
      {icon[status]}{status.toUpperCase()}
    </span>
  );
}

function Tag({ label, color = 'default' }: { label: string; color?: 'default' | 'blue' | 'green' | 'red' }) {
  const cls = {
    default: 'bg-bg-panel text-text-secondary border-border-default',
    blue:    'bg-accent/10 text-accent border-accent/20',
    green:   'bg-green-500/10 text-green-400 border-green-500/20',
    red:     'bg-red-500/10 text-red-400 border-red-500/20',
  }[color];
  return <span className={`inline-block text-[10px] px-1.5 py-0.5 rounded border ${cls}`}>{label}</span>;
}

function Bar({ value, total, color }: { value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-bg-panel overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-text-muted w-8 text-right">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border-default bg-bg-secondary overflow-hidden">
      <div className="px-3 py-2 bg-bg-panel border-b border-border-default">
        <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">{title}</span>
      </div>
      <div className="p-3">{children}</div>
    </div>
  );
}

function FolderCard({ result }: { result: FolderResult }) {
  const [open, setOpen] = useState(result.emails_attributed > 0 || !!result.error);
  const total = result.emails_fetched;

  return (
    <div className="border border-border-default rounded overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-bg-panel hover:bg-bg-secondary transition-colors text-left"
      >
        {open ? <VscChevronDown size={11} /> : <VscChevronRight size={11} />}
        <span className="text-xs font-medium text-text-primary flex-1">{result.folder}</span>
        {!result.found_in_outlook && <Tag label="NOT IN OUTLOOK" color="red" />}
        {result.error && <Tag label="ERROR" color="red" />}
        <span className="text-[10px] text-text-muted">
          {result.emails_fetched} fetched · {result.emails_attributed} matched · {result.emails_rejected} skipped
        </span>
      </button>

      {open && (
        <div className="px-3 py-2.5 space-y-3">
          {result.error && (
            <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-2 py-1.5">
              {result.error}
            </div>
          )}

          {total > 0 && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-text-muted mb-1">
                <span>matched</span><span>{result.emails_attributed}/{total}</span>
              </div>
              <Bar value={result.emails_attributed} total={total} color="bg-green-500" />
              <div className="flex items-center justify-between text-[10px] text-text-muted mt-1">
                <span>skipped</span><span>{result.emails_rejected}/{total}</span>
              </div>
              <Bar value={result.emails_rejected} total={total} color="bg-border-default" />
            </div>
          )}

          {result.sample.length > 0 && (
            <div>
              <div className="text-[10px] text-text-muted mb-1.5 uppercase tracking-wide">Matched emails (sample)</div>
              <div className="space-y-1">
                {result.sample.map((s, i) => (
                  <div key={i} className="flex items-start gap-2 p-1.5 rounded bg-bg-panel">
                    <VscCheck size={10} className="text-green-400 mt-0.5 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs text-text-primary truncate">{s.subject || '(no subject)'}</div>
                      <div className="text-[10px] text-text-muted truncate">{s.sender}</div>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        <Tag label={s.match} color="green" />
                        <Tag label={new Date(s.received_at).toLocaleDateString()} />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.rejection_reasons.length > 0 && (
            <div>
              <div className="text-[10px] text-text-muted mb-1.5 uppercase tracking-wide">Skipped emails (sample)</div>
              <div className="space-y-1">
                {result.rejection_reasons.map((r, i) => (
                  <div key={i} className="flex items-start gap-2 p-1.5 rounded bg-bg-panel">
                    <VscClose size={10} className="text-text-muted mt-0.5 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs text-text-secondary truncate">{r.subject || '(no subject)'}</div>
                      <div className="text-[10px] text-text-muted truncate">{r.sender}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {total === 0 && !result.error && (
            <p className="text-[10px] text-text-muted">No emails fetched from this folder in the last 7 days.</p>
          )}
        </div>
      )}
    </div>
  );
}

function AccountCard({ result }: { result: AccountResult }) {
  const [open, setOpen] = useState(true);
  const totalFetched = result.folders_scanned.reduce((s, f) => s + f.emails_fetched, 0);
  const totalMatched = result.folders_scanned.reduce((s, f) => s + f.emails_attributed, 0);

  return (
    <div className="border border-border-default rounded overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2.5 bg-bg-secondary hover:bg-bg-panel transition-colors text-left"
      >
        {open ? <VscChevronDown size={12} /> : <VscChevronRight size={12} />}
        <span className="text-xs font-semibold text-text-primary flex-1">{result.account}</span>
        <span className="text-[10px] text-text-muted">
          {totalFetched} fetched · <span className="text-green-400">{totalMatched} matched</span>
        </span>
      </button>

      {open && (
        <div className="px-3 pb-3 pt-1 space-y-2">
          {result.outlook_folders_available.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              <span className="text-[10px] text-text-muted mr-1">Available in Outlook:</span>
              {result.outlook_folders_available.map((f) => <Tag key={f} label={f} />)}
            </div>
          )}
          {result.folders_scanned.map((f) => (
            <FolderCard key={f.folder} result={f} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props { clientName: string }

export function ScanDebug({ clientName }: Props) {
  const { apiFetch } = useApiFetch();
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<DebugReport | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  async function runDiagnostic() {
    setRunning(true);
    setFetchError(null);
    setReport(null);
    try {
      const res = await apiFetch(
        `/api/communication/${encodeURIComponent(clientName)}/debug`,
      );
      if (!res.ok) {
        const text = await res.text();
        setFetchError(`Server returned ${res.status}: ${text}`);
        return;
      }
      const data: DebugReport = await res.json();
      setReport(data);
    } catch (e) {
      setFetchError(String(e));
    } finally {
      setRunning(false);
    }
  }

  const outlookBadge = !report ? 'info'
    : report.outlook.status === 'ok' ? 'ok'
    : report.outlook.status === 'unavailable' ? 'warn'
    : 'error';

  const configBadge = !report ? 'info'
    : report.config.status === 'ok' ? 'ok'
    : report.config.status === 'not_found' ? 'warn'
    : 'error';

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4 max-w-3xl">
      {/* Header row */}
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-text-primary">Scan Diagnostics</h2>
          <p className="text-[10px] text-text-muted mt-0.5">
            Runs the full scan pipeline without writing to the database. Shows Outlook connectivity,
            config validity, and a per-folder attribution preview.
          </p>
        </div>
        <button
          type="button"
          onClick={runDiagnostic}
          disabled={running}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded bg-accent text-bg-primary hover:bg-accent/90 disabled:opacity-50 transition-colors shrink-0"
        >
          <VscBeaker size={12} className={running ? 'animate-pulse' : ''} />
          {running ? 'Running…' : report ? 'Re-run' : 'Run Diagnostic'}
        </button>
      </div>

      {/* Fetch-level error */}
      {fetchError && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded px-3 py-2">
          {fetchError}
        </div>
      )}

      {report && (
        <>
          {/* Top-level errors */}
          {report.errors.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/20 rounded p-3 space-y-1">
              <div className="text-[10px] font-semibold text-red-400 uppercase tracking-wide mb-1">Errors</div>
              {report.errors.map((e, i) => (
                <div key={i} className="text-xs text-red-400">{e}</div>
              ))}
            </div>
          )}

          {/* Status cards */}
          <div className="grid grid-cols-2 gap-3">
            <Section title="Outlook">
              <div className="flex items-center gap-2 mb-2">
                <StatusBadge status={outlookBadge as 'ok' | 'warn' | 'error' | 'info'} />
                <span className="text-xs text-text-secondary">{report.outlook.status}</span>
              </div>
              {report.outlook.accounts && report.outlook.accounts.length > 0 ? (
                <div className="space-y-1">
                  {report.outlook.accounts.map((a) => (
                    <div key={a} className="text-[10px] text-text-primary">{a}</div>
                  ))}
                </div>
              ) : (
                <p className="text-[10px] text-text-muted">No accounts found</p>
              )}
            </Section>

            <Section title="Config">
              <div className="flex items-center gap-2 mb-2">
                <StatusBadge status={configBadge as 'ok' | 'warn' | 'error' | 'info'} />
                <span className="text-xs text-text-secondary">{report.config.status}</span>
              </div>
              {report.config.hint && (
                <p className="text-[10px] text-yellow-400">{report.config.hint}</p>
              )}
              {report.config.status === 'ok' && (
                <div className="space-y-1.5 text-[10px] text-text-secondary">
                  <div>
                    <span className="text-text-muted">Domains: </span>
                    {report.config.domains?.length
                      ? report.config.domains.map((d) => <Tag key={d} label={d} color="blue" />)
                      : <span className="text-yellow-400">none</span>}
                  </div>
                  <div>
                    <span className="text-text-muted">Keywords: </span>
                    {report.config.keywords?.length
                      ? report.config.keywords.map((k) => <Tag key={k} label={k} color="blue" />)
                      : <span className="text-yellow-400">none</span>}
                  </div>
                  <div>
                    <span className="text-text-muted">Contacts: </span>
                    {report.config.contacts?.length
                      ? report.config.contacts.map((c) => <Tag key={c} label={c} color="blue" />)
                      : <span className="text-yellow-400">none</span>}
                  </div>
                  <div>
                    <span className="text-text-muted">Accounts: </span>
                    {report.config.accounts?.length
                      ? report.config.accounts.map((a) => <Tag key={a.display_name} label={a.display_name} />)
                      : <span className="text-yellow-400">none</span>}
                  </div>
                </div>
              )}
            </Section>
          </div>

          {/* Scan preview */}
          {report.scan_preview.length > 0 && (
            <div className="space-y-2">
              <div className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">
                Scan Preview — last 7 days
              </div>
              {report.scan_preview.map((a) => (
                <AccountCard key={a.account} result={a} />
              ))}
            </div>
          )}

          {/* No preview */}
          {report.scan_preview.length === 0 && report.config.status === 'ok' && (
            <p className="text-xs text-text-muted">
              No accounts configured — add an Outlook account in the Config tab.
            </p>
          )}

          {/* Raw JSON toggle */}
          <details className="text-[10px] text-text-muted">
            <summary className="cursor-pointer hover:text-text-primary">Raw JSON</summary>
            <pre className="mt-2 p-2 bg-bg-panel rounded overflow-x-auto text-[10px] text-text-secondary whitespace-pre-wrap">
              {JSON.stringify(report, null, 2)}
            </pre>
          </details>
        </>
      )}

      {!report && !running && !fetchError && (
        <div className="flex items-center justify-center h-40 text-text-muted text-xs">
          Press "Run Diagnostic" to test the full scan pipeline.
        </div>
      )}
    </div>
  );
}
