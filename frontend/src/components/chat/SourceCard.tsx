import type { SourceChip } from '@/types';
import { VscFile } from 'react-icons/vsc';

interface Props {
  source: SourceChip;
}

export function SourceCard({ source }: Props) {
  const fileName = source.file_path.split('/').pop() || source.file_path;

  return (
    <button
      className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] bg-accent-blue/10 text-accent-blue hover:bg-accent-blue/20 transition-colors border border-accent-blue/20"
      title={source.excerpt || source.file_path}
    >
      <VscFile size={12} />
      <span className="truncate max-w-[120px]">{fileName}</span>
      {source.section_title && (
        <span className="text-text-muted truncate max-w-[80px]">&middot; {source.section_title}</span>
      )}
      {source.page_number && (
        <span className="text-text-muted">p.{source.page_number}</span>
      )}
    </button>
  );
}
