import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { SourceCard } from './SourceCard';
import type { SourceChip } from '@/types';

interface Props {
  content: string;
  sources: SourceChip[];
}

export function StreamingResponse({ content, sources }: Props) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        {sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {sources.map((source, i) => (
              <SourceCard key={i} source={source} />
            ))}
          </div>
        )}
        <div className="bg-bg-panel rounded-md px-4 py-3 text-sm text-text-primary">
          <div className="prose prose-invert prose-sm max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
            <span className="inline-block w-2 h-4 bg-accent ml-0.5 animate-blink" />
          </div>
        </div>
      </div>
    </div>
  );
}
