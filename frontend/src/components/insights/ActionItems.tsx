import { useState } from 'react';
import { VscChevronDown } from 'react-icons/vsc';
import { format } from 'date-fns';
import type { ActionItem } from '@/types';

interface Props {
  items: ActionItem[];
  clientName: string;
}

export function ActionItems({ items }: Props) {
  const [collapsed, setCollapsed] = useState(false);

  if (!items?.length) return null;

  return (
    <div className="bg-bg-secondary rounded-md p-3 border border-border-default">
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-between w-full group"
      >
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          Action Items
          <span className="ml-1.5 font-normal text-text-muted normal-case tracking-normal">
            ({items.filter((i) => !i.completed).length} open)
          </span>
        </h3>
        <VscChevronDown
          size={12}
          className={`text-text-muted transition-transform duration-150 ${collapsed ? '-rotate-90' : ''}`}
          aria-hidden="true"
        />
      </button>
      {!collapsed && (
        <div className="mt-2 space-y-2">
          {items.map((item, i) => (
            <div key={i} className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={item.completed}
                readOnly
                aria-label={item.description}
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
                    <span className={`text-[10px] ${new Date(item.due_date) < new Date() && !item.completed ? 'text-red-400' : 'text-text-muted'}`}>
                      Due: {format(new Date(item.due_date), 'MMM d')}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
