// frontend/src/components/chat/BriefingCard.tsx
import { VscClose } from 'react-icons/vsc';
import type { BriefingData } from '@/types';

interface Props {
  briefing: BriefingData;
  onDismiss: () => void;
}

export function BriefingCard({ briefing, onDismiss }: Props) {
  const { overdue_items, new_analyses, risk_changes } = briefing;

  return (
    <div className="bg-bg-panel border border-border-default border-l-4 border-l-accent rounded-md p-4 mb-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-sm font-medium text-text-primary">
          Welcome back &mdash; here&rsquo;s what changed
        </h3>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss briefing"
          className="p-0.5 rounded text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors focus:outline-none focus:ring-2 focus:ring-accent-blue"
        >
          <VscClose className="w-4 h-4" />
        </button>
      </div>

      {/* Overdue Items */}
      {overdue_items.length > 0 && (
        <details className="mt-2">
          <summary className="text-xs font-medium text-status-red cursor-pointer select-none">
            Overdue Items ({overdue_items.length})
          </summary>
          <ul className="mt-1 space-y-1 pl-3">
            {overdue_items.map((item, i) => (
              <li key={i} className="text-xs text-text-secondary">
                <span>{item.description}</span>
                {item.due_date && (
                  <span className="ml-1 text-text-muted">
                    &mdash; due {item.due_date}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* New Analyses */}
      {new_analyses.length > 0 && (
        <details className="mt-2">
          <summary className="text-xs font-medium text-accent-blue cursor-pointer select-none">
            New Analyses ({new_analyses.length})
          </summary>
          <ul className="mt-1 space-y-1 pl-3">
            {new_analyses.map((item, i) => (
              <li key={i} className="text-xs text-text-secondary">
                <span className="text-text-primary">{item.file_path}</span>
                <span className="ml-1 text-text-muted">{item.doc_type}</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {/* Risk Changes */}
      {risk_changes.length > 0 && (
        <details className="mt-2">
          <summary className="text-xs font-medium text-status-amber cursor-pointer select-none">
            Risk Changes ({risk_changes.length})
          </summary>
          <ul className="mt-1 space-y-1 pl-3">
            {risk_changes.map((item, i) => (
              <li key={i} className="text-xs text-text-secondary">
                <span>{item.description}</span>
                <span className="ml-1 text-text-muted">({item.severity})</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
