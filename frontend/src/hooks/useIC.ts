import { useState, useEffect } from 'react';
import type { ICData } from '../types';
import { loadIC } from '../lib/dataLoader';

export function useIC() {
  const [data, setData] = useState<ICData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadIC()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading };
}
