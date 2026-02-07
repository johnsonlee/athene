import { useState, useEffect } from 'react';
import type { LeadingIndicatorsData } from '../types';
import { loadLeadingIndicators } from '../lib/dataLoader';

export function useLeadingIndicators() {
  const [data, setData] = useState<LeadingIndicatorsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLeadingIndicators()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
