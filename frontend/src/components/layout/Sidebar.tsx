// frontend/src/components/layout/Sidebar.tsx
import { useRef, useState, useEffect } from 'react';
import { useClientStore } from '@/stores/clientStore';
import { FileTree } from '@/components/filebrowser/FileTree';
import { FileUpload } from '@/components/filebrowser/FileUpload';
import { ToolBrowser } from '@/components/tools/ToolBrowser';
import { useFileTree } from '@/hooks/useFileTree';
import { useSync, type FileEvent } from '@/hooks/useSync';
import { VscRefresh, VscSync } from 'react-icons/vsc';

function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function EventRow({ ev }: { ev: FileEvent }) {
  if (ev.status === 'error') {
    return (
      <div className="flex items-start gap-1 text-[10px] leading-tight">
        <span className="text-red-400 shrink-0 mt-px">✗</span>
        <span className="text-red-400 truncate flex-1" title={ev.error}>{ev.file_name}</span>
        <span className="text-red-400/70 shrink-0 ml-1 truncate max-w-[90px]" title={ev.error}>{ev.error}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1 text-[10px] leading-tight">
      <span className="text-accent shrink-0">✓</span>
      <span className="text-text-muted truncate flex-1">{ev.file_name}</span>
      <span className="text-text-muted/60 shrink-0 ml-1 whitespace-nowrap">
        {ev.chunks} chunks · {formatDuration(ev.duration_ms ?? 0)}
      </span>
    </div>
  );
}

export function Sidebar() {
  const { sidebarTab, setSidebarTab } = useClientStore();
  const { isLoading, refresh } = useFileTree();
  const { sync, isSyncing, progress, error } = useSync();
  const [showSyncMenu, setShowSyncMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!showSyncMenu) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowSyncMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showSyncMenu]);

  return (
    <div className="flex flex-col h-full bg-bg-panel">
      {/* Tab bar */}
      <div className="flex border-b border-border-default shrink-0">
        {(['files', 'tools'] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setSidebarTab(tab)}
            className={`flex-1 py-2 text-xs font-semibold uppercase tracking-wider transition-colors ${
              sidebarTab === tab
                ? 'text-accent border-b-2 border-accent'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {sidebarTab === 'files' && (
        <>
          <div className="flex items-center justify-between px-3 h-8 shrink-0">
            <span className="text-[10px] text-text-muted uppercase">Explorer</span>
            <div className="flex items-center gap-2">
              {/* Sync button with mode dropdown */}
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => !isSyncing && setShowSyncMenu((v) => !v)}
                  disabled={isSyncing}
                  className="text-text-muted hover:text-text-primary transition-colors disabled:opacity-50"
                  title={isSyncing ? `Syncing ${progress.processed}/${progress.total}` : 'Sync knowledge'}
                >
                  <VscSync size={14} className={isSyncing ? 'animate-spin' : ''} />
                </button>
                {showSyncMenu && (
                  <div className="absolute right-0 top-full mt-1 z-50 bg-bg-panel border border-border-default rounded shadow-lg min-w-[190px]">
                    <button
                      type="button"
                      onClick={() => { setShowSyncMenu(false); sync('incremental'); }}
                      className="flex flex-col w-full px-3 py-2 text-left hover:bg-bg-hover transition-colors"
                    >
                      <span className="text-xs text-text-primary">Incremental Sync</span>
                      <span className="text-[10px] text-text-muted">New &amp; changed files only</span>
                    </button>
                    <div className="border-t border-border-default" />
                    <button
                      type="button"
                      onClick={() => { setShowSyncMenu(false); sync('complete'); }}
                      className="flex flex-col w-full px-3 py-2 text-left hover:bg-bg-hover transition-colors"
                    >
                      <span className="text-xs text-text-primary">Complete Sync</span>
                      <span className="text-[10px] text-text-muted">Re-index all files</span>
                    </button>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={refresh}
                className="text-text-muted hover:text-text-primary transition-colors"
                title="Refresh"
              >
                <VscRefresh size={14} className={isLoading ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>

          {/* Sync progress panel */}
          {(isSyncing || error) && (
            <div className="px-3 py-2 border-b border-border-default">
              {isSyncing ? (
                <>
                  {/* Header row: label + file counter */}
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-text-muted">Syncing knowledge…</span>
                    <span className="text-[10px] text-text-muted font-medium">
                      {progress.total > 0
                        ? `File ${progress.fileIndex} / ${progress.total}${progress.skipped > 0 ? ` · ${progress.skipped} unchanged` : ''}`
                        : 'Discovering files…'}
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="h-1 bg-bg-secondary rounded overflow-hidden mb-1">
                    {progress.total > 0 ? (
                      <div
                        className="h-full rounded bg-accent transition-all duration-500"
                        style={{ width: `${Math.round((progress.fileIndex / progress.total) * 100)}%` }}
                      />
                    ) : (
                      <div className="h-full w-1/3 rounded bg-accent/50 animate-pulse" />
                    )}
                  </div>

                  {/* Current file + percentage */}
                  {progress.total > 0 && (
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] text-text-muted truncate max-w-[160px]">
                        {progress.currentFile
                          ? (progress.currentFile.split(/[\\/]/).pop() || progress.currentFile)
                          : ''}
                      </span>
                      <span className="text-[10px] text-text-muted shrink-0 ml-1">
                        {Math.round((progress.fileIndex / progress.total) * 100)}%
                      </span>
                    </div>
                  )}

                  {/* Per-file event log (last 4) */}
                  {progress.fileEvents.length > 0 && (
                    <div className="mt-1 pt-1 border-t border-border-default space-y-0.5">
                      {progress.fileEvents.slice(-4).map((ev, i) => (
                        <EventRow key={i} ev={ev} />
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <span className="text-[10px] text-red-400">Sync error: {error}</span>
              )}
            </div>
          )}

          <FileUpload />
          <div className="flex-1 overflow-y-auto px-1 py-1">
            <FileTree />
          </div>
        </>
      )}

      {sidebarTab === 'tools' && (
        <div className="flex-1 overflow-y-auto">
          <ToolBrowser />
        </div>
      )}
    </div>
  );
}
