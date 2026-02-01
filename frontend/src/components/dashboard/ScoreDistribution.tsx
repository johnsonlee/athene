import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { RankedStock } from '../../types';

interface Props {
  rankings: RankedStock[];
}

export function ScoreDistribution({ rankings }: Props) {
  const data = useMemo(() => {
    const bins = 20;
    const scores = rankings.map((r) => r.composite_score);
    const min = Math.min(...scores);
    const max = Math.max(...scores);
    const range = max - min || 1;
    const binWidth = range / bins;

    const histogram = Array.from({ length: bins }, (_, i) => ({
      label: (min + i * binWidth).toFixed(2),
      count: 0,
    }));

    scores.forEach((score) => {
      const idx = Math.min(Math.floor((score - min) / binWidth), bins - 1);
      histogram[idx].count++;
    });

    return histogram;
  }, [rankings]);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-gray-900">Score Distribution</h2>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
