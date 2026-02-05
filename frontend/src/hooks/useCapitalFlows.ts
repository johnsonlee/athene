import { useState, useEffect } from 'react';
import type { CapitalFlowData } from '../types';
import { loadCapitalFlows } from '../lib/dataLoader';

export function useCapitalFlows() {
  const [data, setData] = useState<CapitalFlowData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCapitalFlows()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
