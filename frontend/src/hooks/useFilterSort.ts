import { useState, useMemo } from 'react';
import type { RankedStock, FilterState } from '../types';

const defaultFilter: FilterState = {
  search: '',
  sectors: [],
  tiers: [],
  minScore: -Infinity,
  maxScore: Infinity,
};

export function useFilterSort(data: RankedStock[]) {
  const [filter, setFilter] = useState<FilterState>(defaultFilter);

  const filtered = useMemo(() => {
    return data.filter((stock) => {
      if (filter.search) {
        const q = filter.search.toLowerCase();
        const matches =
          stock.ticker.toLowerCase().includes(q) ||
          (stock.name?.toLowerCase().includes(q) ?? false);
        if (!matches) return false;
      }
      if (filter.sectors.length > 0 && stock.sector) {
        if (!filter.sectors.includes(stock.sector)) return false;
      }
      if (filter.tiers.length > 0) {
        if (!filter.tiers.includes(stock.tier)) return false;
      }
      if (stock.composite_score < filter.minScore) return false;
      if (stock.composite_score > filter.maxScore) return false;
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
