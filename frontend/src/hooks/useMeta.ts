import { useState, useEffect } from 'react';
import type { Meta } from '../types';
import { loadMeta } from '../lib/dataLoader';

export function useMeta() {
  const [data, setData] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMeta()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { data, loading };
}
