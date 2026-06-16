import { useState } from 'react';
import { VscChevronDown } from 'react-icons/vsc';
import type { Stakeholder } from '@/types';

interface Props {
  stakeholders: Stakeholder[];
  onSelect: (s: Stakeholder) => void;
}

export function StakeholderList({ stakeholders, onSelect }: Props) {
  const [collapsed, setCollapsed] = useState(false);

  if (!stakeholders?.length) return null;

  return (
    <div className="bg-bg-secondary rounded-md p-3 border border-border-default">
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-between w-full group"
      >
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          Key Stakeholders
          <span className="ml-1.5 font-normal text-text-muted normal-case tracking-normal">
            ({stakeholders.length})
          </span>
        </h3>
        <VscChevronDown
          size={12}
          className={`text-text-muted transition-transform duration-150 ${collapsed ? '-rotate-90' : ''}`}
          aria-hidden="true"
        />
      </button>
      {!collapsed && (
        <div className="mt-2 space-y-1">
          {stakeholders.map((s, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onSelect(s)}
              className="flex items-center gap-2 w-full rounded px-1.5 py-1 -mx-1.5 hover:bg-bg-panel transition-colors text-left group/row"
            >
              <div className="w-7 h-7 rounded-full bg-accent/20 flex items-center justify-center text-[10px] font-bold text-accent shrink-0">
                {s.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs text-text-primary truncate group-hover/row:text-accent transition-colors">
                  {s.name}
                </div>
                {s.title && <div className="text-[10px] text-text-muted truncate">{s.title}</div>}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
