// frontend/src/components/communication/CommunicationView.tsx
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { VscArrowLeft, VscRefresh } from 'react-icons/vsc';
import { useThreads, useThread, useMeetings, triggerScan } from '../../hooks/useCommunication';
import { ThreadList } from './ThreadList';
import { ThreadDetail } from './ThreadDetail';
import { ThreadInsightsPanel } from './ThreadInsightsPanel';
import { MeetingLogList } from './MeetingLogList';
import { DraftReplyPanel } from './DraftReplyPanel';
import { CommConfig } from './CommConfig';
import type { EmailThread } from '../../types';

type Tab = 'emails' | 'meetings' | 'drafts' | 'config';

export function CommunicationView() {
  const { clientName = '' } = useParams<{ clientName: string }>();
  const navigate = useNavigate();
  const decodedName = decodeURIComponent(clientName);

  const [activeTab, setActiveTab] = useState<Tab>('emails');
  const [selectedThread, setSelectedThread] = useState<EmailThread | null>(null);
  const [insightsCollapsed, setInsightsCollapsed] = useState(false);
  const [scanning, setScanning] = useState(false);

  const { threads, loading: threadsLoading, reload: reloadThreads } = useThreads(decodedName);
  const { emails, subject, loading: threadLoading } = useThread(decodedName, selectedThread?.thread_key ?? null);
  const { meetings, loading: meetingsLoading, reload: reloadMeetings } = useMeetings(decodedName);

  function handleTabChange(t: Tab) {
    setActiveTab(t);
  }

  async function handleScan() {
    setScanning(true);
    try {
      await triggerScan(decodedName);
      setTimeout(() => { reloadThreads(); reloadMeetings(); }, 2500);
    } finally {
      setScanning(false);
    }
  }

  function handleDraftCreated() {
    // Switch to Drafts tab after generating a reply
    handleTabChange('drafts');
    reloadThreads();
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'emails', label: 'Emails' },
    { id: 'meetings', label: 'Meetings' },
    { id: 'drafts', label: 'Drafts' },
    { id: 'config', label: 'Config' },
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
            {/* Left: Thread list */}
            <ThreadList
              threads={threads}
              loading={threadsLoading}
              selectedKey={selectedThread?.thread_key ?? null}
              onSelect={setSelectedThread}
              onSearch={(q) => reloadThreads(q)}
            />

            {/* Centre: Thread detail */}
            <ThreadDetail
              emails={emails}
              subject={subject}
              loading={threadLoading}
              clientName={decodedName}
              onGenerateReply={handleDraftCreated}
            />

            {/* Right: AI insights */}
            <ThreadInsightsPanel
              clientName={decodedName}
              threadKey={selectedThread?.thread_key ?? null}
              collapsed={insightsCollapsed}
              onToggleCollapse={() => setInsightsCollapsed((c) => !c)}
            />
          </div>
        )}

        {/* ── Meetings tab ── */}
        {activeTab === 'meetings' && (
          <div className="h-full overflow-y-auto">
            <MeetingLogList
              meetings={meetings}
              loading={meetingsLoading}
              onReload={reloadMeetings}
            />
          </div>
        )}

        {/* ── Drafts tab ── */}
        {activeTab === 'drafts' && (
          <div className="h-full overflow-hidden">
            <DraftReplyPanel clientName={decodedName} />
          </div>
        )}

        {/* ── Config tab ── */}
        {activeTab === 'config' && (
          <div className="h-full overflow-y-auto">
            <CommConfig clientName={decodedName} />
          </div>
        )}
      </main>
    </div>
  );
}
