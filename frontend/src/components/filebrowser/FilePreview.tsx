// frontend/src/components/filebrowser/FilePreview.tsx
import { useState, useEffect } from 'react';
import { VscClose } from 'react-icons/vsc';

interface Props {
  path: string;
  onClose: () => void;
}

export function FilePreview({ path, onClose }: Props) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/files/preview?path=${encodeURIComponent(path)}`)
      .then((res) => res.json())
      .then((data) => setContent(data.content || 'No content'))
      .catch(() => setContent('Failed to load preview'))
      .finally(() => setLoading(false));
  }, [path]);

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-bg-panel border border-border-default rounded-md max-w-3xl w-full max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-default">
          <span className="text-sm font-medium text-text-primary truncate">{path}</span>
          <button type="button" onClick={onClose} className="text-text-muted hover:text-text-primary" aria-label="Close preview">
            <VscClose size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="text-text-muted text-sm">Loading...</div>
          ) : (
            <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap">{content}</pre>
          )}
        </div>
      </div>
    </div>
  );
}
