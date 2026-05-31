// frontend/src/components/layout/AppShell.tsx
import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useClientStore } from '@/stores/clientStore';
import { useTheme } from '@/contexts/ThemeContext';
import { Sidebar } from './Sidebar';
import { InsightsPanel } from './InsightsPanel';
import { ChatTerminal } from '@/components/chat/ChatTerminal';
import { MCPServerPanel } from '@/components/settings/MCPServerPanel';
import { ToastContainer } from '@/components/common/Toast';
import { VscLayoutSidebarLeft, VscLayoutSidebarRight, VscArrowLeft } from 'react-icons/vsc';
import { BsSun, BsMoon } from 'react-icons/bs';

export function AppShell() {
  const navigate = useNavigate();
  const { isDark, toggleTheme } = useTheme();
  const {
    leftPanelWidth, rightPanelWidth,
    leftPanelCollapsed, rightPanelCollapsed,
    setLeftPanelWidth, setRightPanelWidth,
    toggleLeftPanel, toggleRightPanel,
    mcpServers, lastIndexed, activeClient,
  } = useClientStore();

  const [isMobile, setIsMobile] = useState(false);
  const [activeTab, setActiveTab] = useState<'files' | 'chat' | 'insights'>('chat');
  const [resizing, setResizing] = useState<'left' | 'right' | null>(null);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const onMouseDown = useCallback((side: 'left' | 'right') => {
    setResizing(side);
  }, []);

  useEffect(() => {
    if (!resizing) return;
    const onMove = (e: MouseEvent) => {
      if (resizing === 'left') {
        setLeftPanelWidth(Math.max(200, Math.min(500, e.clientX)));
      } else {
        setRightPanelWidth(Math.max(200, Math.min(500, window.innerWidth - e.clientX)));
      }
    };
    const onUp = () => setResizing(null);
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
  }, [resizing, setLeftPanelWidth, setRightPanelWidth]);

  if (isMobile) {
    return (
      <div className="flex flex-col h-screen bg-bg-primary">
        <header className="flex items-center justify-between px-4 h-12 bg-bg-secondary border-b border-border-default">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="text-text-muted hover:text-text-primary transition-colors"
              aria-label="Back to all clients"
            >
              <VscArrowLeft size={16} />
            </button>
            <span className="text-sm font-semibold text-accent">{activeClient || 'CIA'}</span>
          </div>
          <button
            type="button"
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="text-text-muted hover:text-text-primary transition-colors p-1 rounded"
          >
            {isDark ? <BsSun size={14} /> : <BsMoon size={14} />}
          </button>
        </header>
        <div className="flex-1 overflow-hidden">
          {activeTab === 'files' && <Sidebar />}
          {activeTab === 'chat' && <ChatTerminal />}
          {activeTab === 'insights' && <InsightsPanel />}
        </div>
        <nav className="flex h-12 bg-bg-secondary border-t border-border-default">
          {(['files', 'chat', 'insights'] as const).map((tab) => (
            <button
              type="button"
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 text-xs font-medium capitalize transition-colors duration-150 ${
                activeTab === tab ? 'text-accent' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-bg-primary">
      {/* Header */}
      <header className="flex items-center justify-between px-4 h-12 bg-bg-secondary border-b border-border-default shrink-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-text-muted hover:text-text-primary transition-colors"
            aria-label="Back to all clients"
          >
            <VscArrowLeft size={16} />
          </button>
          <span className="text-sm font-bold text-accent tracking-wide">{activeClient || 'CLIENT INTELLIGENCE AGENT'}</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="text-text-muted hover:text-text-primary transition-colors p-1 rounded"
          >
            {isDark ? <BsSun size={14} /> : <BsMoon size={14} />}
          </button>
          <div className="w-2 h-2 rounded-full bg-accent animate-pulse-dot" title="System active" />
        </div>
      </header>

      {/* Main panels */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: File Browser */}
        {!leftPanelCollapsed && (
          <>
            <div style={{ width: leftPanelWidth }} className="shrink-0 overflow-hidden border-r border-border-default">
              <Sidebar />
            </div>
            <div
              className="w-1 cursor-col-resize bg-border-default hover:bg-accent transition-colors duration-150 shrink-0"
              onMouseDown={() => onMouseDown('left')}
            />
          </>
        )}

        {/* Center: Chat */}
        <div className="flex-1 overflow-hidden">
          <ChatTerminal />
        </div>

        {/* Right: Insights */}
        {!rightPanelCollapsed && (
          <>
            <div
              className="w-1 cursor-col-resize bg-border-default hover:bg-accent transition-colors duration-150 shrink-0"
              onMouseDown={() => onMouseDown('right')}
            />
            <div style={{ width: rightPanelWidth }} className="shrink-0 overflow-hidden border-l border-border-default">
              <InsightsPanel />
            </div>
          </>
        )}
      </div>

      {/* Status bar */}
      <footer className="flex items-center justify-between px-4 h-8 bg-bg-secondary border-t border-border-default text-xs text-text-muted shrink-0">
        <div className="flex items-center gap-3">
          <button type="button" onClick={toggleLeftPanel} className="hover:text-text-primary transition-colors" title="Toggle files">
            <VscLayoutSidebarLeft size={14} />
          </button>
          <span>gpt-4o</span>
        </div>
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => useClientStore.getState().setShowMCPPanel(true)}>
          {mcpServers.map((s) => (
            <span key={s.name} className={`px-2 py-0.5 rounded text-[10px] ${s.connected ? 'bg-accent/20 text-accent' : 'bg-border-default text-text-muted'}`}>
              {s.name}
            </span>
          ))}
          <span className="text-[10px] text-text-muted hover:text-accent-blue cursor-pointer">MCP</span>
        </div>
        <div className="flex items-center gap-3">
          {lastIndexed && <span>Indexed: {new Date(lastIndexed).toLocaleString()}</span>}
          <button type="button" onClick={toggleRightPanel} className="hover:text-text-primary transition-colors" title="Toggle insights">
            <VscLayoutSidebarRight size={14} />
          </button>
        </div>
      </footer>
      <MCPServerPanel />
      <ToastContainer />
    </div>
  );
}
