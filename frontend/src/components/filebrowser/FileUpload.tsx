// frontend/src/components/filebrowser/FileUpload.tsx
import { useState, useRef, useCallback } from 'react';
import { useFileUpload } from '@/hooks/useFileUpload';
import { useClientStore } from '@/stores/clientStore';
import { VscCloudUpload } from 'react-icons/vsc';

export function FileUpload() {
  const { uploadFile } = useFileUpload();
  const uploads = useClientStore((s) => s.uploads);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => uploadFile(f));
  }, [uploadFile]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const activeUploads = Object.values(uploads);

  return (
    <div className="p-2 border-b border-border-default">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center p-4 border-2 border-dashed rounded-md transition-colors ${
          dragging ? 'border-accent bg-accent/5' : 'border-border-default hover:border-accent/50'
        }`}
      >
        <VscCloudUpload size={24} className="text-text-muted mb-1" />
        <label className="text-xs text-text-muted cursor-pointer">
          Drop files or click to upload
          <input
            ref={inputRef}
            type="file"
            multiple
            className="sr-only"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
      </div>

      {activeUploads.length > 0 && (
        <div className="mt-2 space-y-1">
          {activeUploads.map((u) => (
            <div key={u.fileId} className="flex items-center gap-2 text-xs">
              <div className="flex-1 min-w-0">
                <div className="truncate text-text-secondary">{u.fileName}</div>
                <progress
                  value={u.percent}
                  max={100}
                  aria-label={`${u.fileName} upload progress`}
                  className="sr-only"
                >
                  {u.percent}%
                </progress>
                <div className="h-1 bg-bg-secondary rounded mt-0.5" aria-hidden="true">
                  {/* Dynamic width requires inline style -- no Tailwind utility for runtime percentages */}
                  <div
                    className={`h-full rounded transition-all ${
                      u.status === 'error' ? 'bg-red-500' : 'bg-accent'
                    }`}
                    style={{ width: `${u.percent}%` }}
                  />
                </div>
              </div>
              <span className={`text-[10px] shrink-0 ${
                u.status === 'done' ? 'text-accent' :
                u.status === 'error' ? 'text-red-400' :
                u.status === 'analyzing' ? 'text-accent-blue' :
                'text-text-muted'
              }`}>
                {u.status === 'uploading' ? 'Uploading...' :
                 u.status === 'analyzing' ? 'Analyzing...' :
                 u.status === 'done' ? 'Done' :
                 u.status === 'error' ? (u.error || 'Error') : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
