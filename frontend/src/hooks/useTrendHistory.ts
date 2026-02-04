import { useState, useEffect } from 'react';
import type { TrendHistory } from '../types';
import { loadTrendHistory } from '../lib/dataLoader';

export function useTrendHistory() {
  const [data, setData] = useState<TrendHistory | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTrendHistory()
      .then(setData)
      .catch(() => {}) // history is optional — ignore errors
      .finally(() => setLoading(false));
  }, []);

  return { data, loading };
}
