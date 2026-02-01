import { useState, useEffect } from 'react';
import type { RankedStock } from '../types';
import { loadRankings } from '../lib/dataLoader';

export function useRankings() {
  const [data, setData] = useState<RankedStock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRankings()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
