import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { RankedStock } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  rankings: RankedStock[];
}

export function ScoreDistribution({ rankings }: Props) {
  const { t } = useI18n();

  const data = useMemo(() => {
    const bins = 20;
    const binWidth = 100 / bins; // Fixed 0-100 range
    const scores = rankings.map((r) => r.composite_score);

    const histogram = Array.from({ length: bins }, (_, i) => ({
      label: (i * binWidth).toFixed(0),
      count: 0,
    }));

    scores.forEach((score) => {
      const idx = Math.min(Math.floor(score / binWidth), bins - 1);
      histogram[idx].count++;
    });

    return histogram;
  }, [rankings]);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.scoreDistribution')}</h2>
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
