// frontend/src/hooks/useSearch.ts
import { useState, useMemo, useCallback } from 'react';

export interface FilterDef<T> {
  key: string;
  accessor: (item: T) => string;
}

/**
 * Generic faceted filter hook.
 * Filters `items` by matching each item's accessor values against the active filter values.
 *
 * Usage:
 * ```ts
 * const { filtered, activeFilters, setFilter, clearFilter, clearAll } = useSearch(
 *   engagements,
 *   [
 *     { key: 'phase', accessor: (e) => e.phase },
 *     { key: 'status', accessor: (e) => e.status },
 *   ],
 * );
 * ```
 */
export function useSearch<T>(items: T[], filterDefs: FilterDef<T>[]) {
  const [activeFilters, setActiveFilters] = useState<Record<string, string[]>>({});

  const setFilter = useCallback((key: string, values: string[]) => {
    setActiveFilters((prev) => ({ ...prev, [key]: values }));
  }, []);

  const clearFilter = useCallback((key: string) => {
    setActiveFilters((prev) => {
      const { [key]: _, ...rest } = prev;
      return rest;
    });
  }, []);

  const clearAll = useCallback(() => {
    setActiveFilters({});
  }, []);

  const filtered = useMemo(() => {
    const activeKeys = Object.keys(activeFilters).filter(
      (k) => activeFilters[k].length > 0,
    );

    if (activeKeys.length === 0) return items;

    // Build a lookup from key -> accessor for quick access
    const defsByKey = new Map(filterDefs.map((d) => [d.key, d]));

    return items.filter((item) =>
      activeKeys.every((key) => {
        const def = defsByKey.get(key);
        if (!def) return true;
        const value = def.accessor(item);
        return activeFilters[key].includes(value);
      }),
    );
  }, [items, filterDefs, activeFilters]);

  return { filtered, activeFilters, setFilter, clearFilter, clearAll };
}
