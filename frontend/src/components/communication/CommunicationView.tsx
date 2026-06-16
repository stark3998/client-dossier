// frontend/src/components/communication/CommunicationView.tsx
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { VscArrowLeft, VscCheck, VscClose, VscRefresh } from 'react-icons/vsc';
import { useThreads, useThread, useMeetings, useTriggerScan } from '../../hooks/useCommunication';
import { ThreadList } from './ThreadList';
import { ThreadDetail } from './ThreadDetail';
import { ThreadInsightsPanel } from './ThreadInsightsPanel';
import { MeetingLogList } from './MeetingLogList';
import { DraftReplyPanel } from './DraftReplyPanel';
import { CommConfig } from './CommConfig';
import { ScanDebug } from './ScanDebug';
import { useApiFetch } from '../../hooks/useApiFetch';
import type { EmailThread } from '../../types';

type Tab = 'emails' | 'meetings' | 'drafts' | 'config' | 'debug';

interface ScanProgress {
  running: boolean;
  client_name?: string;
  started_at?: string;
  phase?: string;
  current_account?: string | null;
  current_folder?: string | null;
  folder_status?: string | null;
  folder_fetched?: number;
  folder_matched?: number;
  totals_fetched?: number;
  totals_matched?: number;
  totals_new?: number;
  message?: string;
  completed_at?: string | null;
  error?: string | null;
}

function ScanProgressPanel({
  progress,
  onDismiss,
}: {
  progress: ScanProgress;
  onDismiss: () => void;
}) {
  const isDone = !progress.running && progress.phase === 'done';
  const isError = !progress.running && progress.phase === 'error';

  return (
    <div className={`border-t shrink-0 px-5 py-3 text-xs transition-colors ${
      isError ? 'bg-red-950/30 border-red-800/40' :
      isDone  ? 'bg-green-950/20 border-green-800/30' :
                'bg-bg-secondary border-border-default'
    }`}>
      <div className="flex items-start gap-3">
        {/* Spinner / check / error icon */}
        <div className="mt-0.5 shrink-0">
          {progress.running && (
            <VscRefresh size={13} className="animate-spin text-accent" aria-hidden="true" />
          )}
          {isDone && <VscCheck size={13} className="text-green-400" aria-hidden="true" />}
          {isError && <VscClose size={13} className="text-red-400" aria-hidden="true" />}
        </div>

        <div className="flex-1 min-w-0 space-y-1">
          {/* Main status line */}
          <p className={`font-medium truncate ${isError ? 'text-red-300' : isDone ? 'text-green-300' : 'text-text-primary'}`}>
            {progress.message || 'Scanning…'}
          </p>

          {/* Current location */}
          {progress.running && progress.current_account && (
            <p className="text-text-muted">
              <span className="text-text-secondary">{progress.current_account}</span>
              {progress.current_folder && (
                <> / <span className="text-text-secondary">{progress.current_folder}</span>
                  {progress.folder_status && (
                    <span className="ml-1 text-text-muted">({progress.folder_status})</span>
                  )}
                </>
              )}
            </p>
          )}

          {/* Totals */}
          {((progress.totals_fetched ?? 0) > 0 || isDone) && (
            <div className="flex gap-4 text-text-muted">
              <span><span className="text-text-secondary">{progress.totals_fetched ?? 0}</span> fetched</span>
              <span><span className="text-text-secondary">{progress.totals_matched ?? 0}</span> matched</span>
              <span><span className="text-green-400">{progress.totals_new ?? 0}</span> saved</span>
            </div>
          )}
        </div>

        {/* Dismiss (only when done/error) */}
        {!progress.running && (
          <button
            type="button"
            onClick={onDismiss}
            className="text-text-muted hover:text-text-primary shrink-0"
            aria-label="Dismiss"
          >
            <VscClose size={12} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}

export function CommunicationView() {
  const { clientName = '' } = useParams<{ clientName: string }>();
  const navigate = useNavigate();
  const decodedName = decodeURIComponent(clientName);
  const { apiFetch } = useApiFetch();

  const [activeTab, setActiveTab] = useState<Tab>('emails');
  const [selectedThread, setSelectedThread] = useState<EmailThread | null>(null);
  const [insightsCollapsed, setInsightsCollapsed] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { threads, loading: threadsLoading, reload: reloadThreads } = useThreads(decodedName);
  const { emails, subject, loading: threadLoading } = useThread(decodedName, selectedThread?.thread_key ?? null);
  const { meetings, loading: meetingsLoading, reload: reloadMeetings } = useMeetings(decodedName);
  const triggerScan = useTriggerScan();

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function startPolling() {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/communication/${encodeURIComponent(decodedName)}/scan/status`);
        const p: ScanProgress = await res.json();
        setProgress(p);
        if (!p.running) {
          stopPolling();
          setScanning(false);
          // Reload data a beat after completion
          setTimeout(() => { reloadThreads(); reloadMeetings(); }, 1000);
        }
      } catch {
        stopPolling();
        setScanning(false);
      }
    }, 2000);
  }

  // Clean up on unmount
  useEffect(() => () => stopPolling(), []);

  function handleTabChange(t: Tab) { setActiveTab(t); }

  async function handleScan() {
    setScanning(true);
    setProgress({ running: true, message: 'Starting scan…' });
    try {
      await triggerScan(decodedName);
      startPolling();
    } catch {
      setScanning(false);
      setProgress({ running: false, phase: 'error', message: 'Failed to start scan' });
    }
  }

  function handleDraftCreated() {
    handleTabChange('drafts');
    reloadThreads();
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'emails', label: 'Emails' },
    { id: 'meetings', label: 'Meetings' },
    { id: 'drafts', label: 'Drafts' },
    { id: 'config', label: 'Config' },
    { id: 'debug', label: 'Diagnostics' },
  ];

  return (
    <div className="min-h-screen h-screen bg-bg-primary flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex items-center gap-3 px-5 h-12 bg-bg-secondary border-b border-border-default shrink-0">
        <button
          type="button"
          onClick={() => navigate(`/clients/${clientName}`)}
          aria-label="Back to workspace"
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          <VscArrowLeft size={15} aria-hidden="true" />
        </button>
        <h1 className="text-sm font-bold text-text-primary flex-1 truncate">
          Communications — {decodedName}
        </h1>
        <button
          type="button"
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded bg-bg-panel border border-border-default text-text-muted hover:text-text-primary disabled:opacity-50 transition-colors"
          aria-label="Trigger email scan"
        >
          <VscRefresh size={12} className={scanning ? 'animate-spin' : ''} aria-hidden="true" />
          {scanning ? 'Scanning…' : 'Scan now'}
        </button>
      </header>

      {/* Tab bar */}
      <nav className="flex border-b border-border-default bg-bg-secondary shrink-0" aria-label="Communications sections">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => handleTabChange(t.id)}
            className={`px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
              activeTab === t.id
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text-primary'
            }`}
            aria-current={activeTab === t.id ? 'page' : undefined}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main className="flex-1 overflow-hidden">

        {/* ── Emails tab: three-column layout ── */}
        {activeTab === 'emails' && (
          <div className="flex h-full overflow-hidden">
            <ThreadList
              threads={threads}
              loading={threadsLoading}
              selectedKey={selectedThread?.thread_key ?? null}
              onSelect={setSelectedThread}
              onSearch={(q) => reloadThreads(q)}
            />
            <ThreadDetail
              emails={emails}
              subject={subject}
              loading={threadLoading}
              clientName={decodedName}
              onGenerateReply={handleDraftCreated}
            />
            <ThreadInsightsPanel
              clientName={decodedName}
              threadKey={selectedThread?.thread_key ?? null}
              collapsed={insightsCollapsed}
              onToggleCollapse={() => setInsightsCollapsed((c) => !c)}
            />
          </div>
        )}

        {activeTab === 'meetings' && (
          <div className="h-full overflow-y-auto">
            <MeetingLogList meetings={meetings} loading={meetingsLoading} onReload={reloadMeetings} />
          </div>
        )}

        {activeTab === 'drafts' && (
          <div className="h-full overflow-hidden">
            <DraftReplyPanel clientName={decodedName} />
          </div>
        )}

        {activeTab === 'config' && (
          <div className="h-full overflow-y-auto">
            <CommConfig clientName={decodedName} />
          </div>
        )}

        {activeTab === 'debug' && (
          <div className="h-full overflow-hidden">
            <ScanDebug clientName={decodedName} />
          </div>
        )}
      </main>

      {/* Scan progress panel — shown while running or until dismissed */}
      {progress && (
        <ScanProgressPanel
          progress={progress}
          onDismiss={() => setProgress(null)}
        />
      )}
    </div>
  );
}
