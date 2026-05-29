// frontend/src/components/common/Toast.tsx
import { useState, useEffect } from 'react';
import { VscClose, VscCheck, VscWarning, VscInfo } from 'react-icons/vsc';

interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  title: string;
  message: string;
}

let addToastFn: ((toast: Omit<ToastMessage, 'id'>) => void) | null = null;

/** Show a toast notification from anywhere in the app. */
export function showToast(toast: Omit<ToastMessage, 'id'>) {
  addToastFn?.(toast);
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    addToastFn = (toast) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { ...toast, id }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 6000);
    };
    return () => { addToastFn = null; };
  }, []);

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2 max-w-sm" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div
          key={t.id}
          className="flex items-start gap-2 p-3 bg-bg-panel border border-border-default rounded-md shadow-lg animate-slide-in"
        >
          {t.type === 'success' && <VscCheck size={16} className="text-accent shrink-0 mt-0.5" />}
          {t.type === 'error' && <VscWarning size={16} className="text-red-400 shrink-0 mt-0.5" />}
          {t.type === 'info' && <VscInfo size={16} className="text-accent-blue shrink-0 mt-0.5" />}
          <div className="min-w-0 flex-1">
            <div className="text-xs font-medium text-text-primary">{t.title}</div>
            <div className="text-[11px] text-text-secondary mt-0.5">{t.message}</div>
          </div>
          <button
            type="button"
            onClick={() => dismiss(t.id)}
            className="text-text-muted hover:text-text-primary shrink-0"
            aria-label="Dismiss notification"
          >
            <VscClose size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
