// frontend/src/components/communication/ThreadInsightsPanel.tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { VscChevronLeft, VscChevronRight, VscLoading, VscSparkle } from 'react-icons/vsc';
import { useTheme } from '../../contexts/ThemeContext';
import { SourceCard } from '../chat/SourceCard';
import { useThreadInsight } from '../../hooks/useCommunication';

interface Props {
  clientName: string;
  threadKey: string | null;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

function SkeletonLine({ w }: { w: string }) {
  return <div className={`h-3 rounded bg-bg-secondary animate-pulse ${w}`} />;
}

function InsightSkeleton() {
  return (
    <div className="space-y-2 p-4">
      <SkeletonLine w="w-1/3" />
      <SkeletonLine w="w-full" />
      <SkeletonLine w="w-5/6" />
      <SkeletonLine w="w-4/5" />
      <div className="mt-3" />
      <SkeletonLine w="w-1/4" />
      <SkeletonLine w="w-full" />
      <SkeletonLine w="w-3/4" />
    </div>
  );
}

export function ThreadInsightsPanel({ clientName, threadKey, collapsed, onToggleCollapse }: Props) {
  const { isDark } = useTheme();
  const { content, sources, isStreaming, analyze } = useThreadInsight(clientName, threadKey);

  if (collapsed) {
    return (
      <div className="flex flex-col items-center w-8 shrink-0 border-l border-border-default bg-bg-panel py-3 gap-2">
        <button
          type="button"
          onClick={onToggleCollapse}
          className="text-text-muted hover:text-accent transition-colors"
          aria-label="Expand AI Insights"
        >
          <VscChevronLeft size={16} aria-hidden="true" />
        </button>
        <div
          className="text-[9px] text-text-muted writing-mode-vertical"
          style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
        >
          AI Insights
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-80 shrink-0 border-l border-border-default bg-bg-panel">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 h-10 border-b border-border-default shrink-0">
        <VscSparkle size={13} className="text-accent" aria-hidden="true" />
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide flex-1">
          AI Insights
        </span>
        <button
          type="button"
          onClick={onToggleCollapse}
          className="text-text-muted hover:text-accent transition-colors"
          aria-label="Collapse AI Insights"
        >
          <VscChevronRight size={14} aria-hidden="true" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {!threadKey ? (
          <div className="p-4 text-xs text-text-muted">Select a thread to generate insights.</div>
        ) : !content && !isStreaming ? (
          <div className="p-4 flex flex-col gap-3">
            <p className="text-xs text-text-muted leading-relaxed">
              Analyse this email thread with AI. The assistant will summarise the conversation,
              extract action items, flag risks, and surface relevant documents from your knowledge base.
            </p>
            <button
              type="button"
              onClick={analyze}
              className="flex items-center justify-center gap-2 px-3 py-2 text-xs rounded-md bg-accent text-white hover:bg-accent/90 transition-colors"
            >
              <VscSparkle size={12} aria-hidden="true" />
              Analyze Thread
            </button>
          </div>
        ) : (
          <div className="flex flex-col h-full">
            {/* Streaming markdown */}
            <div className="flex-1 overflow-y-auto p-4">
              <div
                className={`prose ${isDark ? 'prose-invert' : ''} prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 text-text-primary`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                {isStreaming && (
                  <span className="inline-block w-2 h-4 bg-accent ml-0.5 animate-blink" />
                )}
              </div>
            </div>

            {/* Sources */}
            {sources.length > 0 && (
              <div className="px-4 pb-3 border-t border-border-default pt-3 shrink-0">
                <div className="text-[10px] text-text-muted uppercase tracking-wide mb-2">
                  Related Documents
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {sources.map((src, i) => (
                    <SourceCard key={i} source={src} />
                  ))}
                </div>
              </div>
            )}

            {/* Re-analyze */}
            {!isStreaming && content && (
              <div className="px-4 pb-3 shrink-0">
                <button
                  type="button"
                  onClick={analyze}
                  className="flex items-center gap-1 text-[10px] text-text-muted hover:text-accent transition-colors"
                >
                  {isStreaming ? (
                    <VscLoading size={10} className="animate-spin" aria-hidden="true" />
                  ) : (
                    <VscSparkle size={10} aria-hidden="true" />
                  )}
                  Re-analyze
                </button>
              </div>
            )}

            {/* Streaming indicator */}
            {isStreaming && (
              <div className="px-4 pb-2 flex items-center gap-1.5 text-[10px] text-text-muted shrink-0">
                <VscLoading size={10} className="animate-spin" aria-hidden="true" />
                Analyzing…
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
