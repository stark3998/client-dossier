// frontend/src/components/layout/Sidebar.tsx
import { useClientStore } from '@/stores/clientStore';
import { FileTree } from '@/components/filebrowser/FileTree';
import { FileUpload } from '@/components/filebrowser/FileUpload';
import { ToolBrowser } from '@/components/tools/ToolBrowser';
import { useFileTree } from '@/hooks/useFileTree';
import { VscRefresh } from 'react-icons/vsc';

export function Sidebar() {
  const { sidebarTab, setSidebarTab } = useClientStore();
  const { isLoading, refresh } = useFileTree();

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
            <button
              type="button"
              onClick={refresh}
              className="text-text-muted hover:text-text-primary transition-colors"
              title="Refresh"
            >
              <VscRefresh size={14} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
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
