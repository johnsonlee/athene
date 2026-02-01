import { useState, useEffect } from 'react';
import type { StockDetail } from '../types';
import { loadStockDetail } from '../lib/dataLoader';

export function useStockDetail(ticker: string | undefined) {
  const [data, setData] = useState<StockDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);
    loadStockDetail(ticker)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [ticker]);

  return { data, loading, error };
}
