import type { ActionItem } from '@/types';
import { format } from 'date-fns';

interface Props {
  items: ActionItem[];
  clientName: string;
}

export function ActionItems({ items }: Props) {
  if (items.length === 0) return null;

  return (
    <div className="bg-bg-secondary rounded-md p-3 border border-border-default">
      <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Action Items</h3>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-2">
            <input
              type="checkbox"
              checked={item.completed}
              readOnly
              className="mt-0.5 rounded border-border-default accent-accent"
            />
            <div className="min-w-0 flex-1">
              <div className={`text-xs ${item.completed ? 'text-text-muted line-through' : 'text-text-primary'}`}>
                {item.description}
              </div>
              <div className="flex gap-2 mt-0.5">
                {item.owner && (
                  <span className="text-[10px] text-text-muted">{item.owner}</span>
                )}
                {item.due_date && (
                  <span className={`text-[10px] ${new Date(item.due_date) < new Date() ? 'text-red-400' : 'text-text-muted'}`}>
                    Due: {format(new Date(item.due_date), 'MMM d')}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
