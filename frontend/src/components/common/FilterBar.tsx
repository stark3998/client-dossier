import { VscClose } from 'react-icons/vsc';

export interface FilterDef {
  key: string;
  label: string;
  options: { value: string; label: string }[];
}

interface Props {
  filters: FilterDef[];
  activeFilters: Record<string, string[]>;
  onChange: (key: string, values: string[]) => void;
  onClear: () => void;
}

export default function FilterBar({ filters, activeFilters, onChange, onClear }: Props) {
  const hasActive = Object.values(activeFilters).some((v) => v.length > 0);

  return (
    <div className="flex items-center gap-2 flex-wrap py-2">
      {filters.map((f) => (
        <select
          key={f.key}
          value={activeFilters[f.key]?.[0] || ''}
          onChange={(e) => onChange(f.key, e.target.value ? [e.target.value] : [])}
          className="bg-bg-primary border border-border-default rounded-md px-2 py-1 text-xs text-text-secondary focus:border-accent outline-none"
        >
          <option value="">{f.label}</option>
          {f.options.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      ))}

      {/* Active filter pills */}
      {Object.entries(activeFilters).map(([key, values]) =>
        values.map((v) => (
          <span
            key={`${key}-${v}`}
            className="flex items-center gap-1 px-2 py-0.5 bg-accent/10 text-accent text-xs rounded-full"
          >
            {v}
            <button
              onClick={() => onChange(key, values.filter((x) => x !== v))}
              className="hover:text-accent-bright"
              aria-label={`Remove ${v} filter`}
            >
              <VscClose className="w-3 h-3" />
            </button>
          </span>
        ))
      )}

      {hasActive && (
        <button onClick={onClear} className="text-xs text-text-muted hover:text-text-secondary">
          Clear all
        </button>
      )}
    </div>
  );
}
