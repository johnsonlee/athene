import { useState, useMemo } from 'react';
import type { RankedStock, FilterState } from '../types';

interface InitialFilters {
  sector?: string;
  minScore?: number;
  maxScore?: number;
}

function buildDefaultFilter(init?: InitialFilters): FilterState {
  return {
    search: '',
    sectors: init?.sector ? [init.sector] : [],
    minScore: init?.minScore ?? -Infinity,
    maxScore: init?.maxScore ?? Infinity,
  };
}

export function useFilterSort(data: RankedStock[], init?: InitialFilters) {
  const [filter, setFilter] = useState<FilterState>(() => buildDefaultFilter(init));

  const filtered = useMemo(() => {
    return data.filter((stock) => {
      if (filter.search) {
        const q = filter.search.toLowerCase();
        const ticker = (stock.ticker || '').toLowerCase();
        const name = (stock.name || '').toLowerCase();
        if (!ticker.includes(q) && !name.includes(q)) return false;
      }
      if (filter.sectors.length > 0 && stock.sector) {
        if (!filter.sectors.includes(stock.sector)) return false;
      }
      const score = stock.alpha_score ?? stock.composite_score ?? 0;
      if (score < filter.minScore) return false;
      if (score > filter.maxScore) return false;
      return true;
    });
  }, [data, filter]);

  const sectors = useMemo(() => {
    const set = new Set<string>();
    data.forEach((s) => { if (s.sector && s.sector !== 'Unknown') set.add(s.sector); });
    return Array.from(set).sort();
  }, [data]);

  return { filtered, filter, setFilter, sectors };
}
