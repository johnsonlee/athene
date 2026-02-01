import { useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { RankedStock } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  rankings: RankedStock[];
}

const BIN_WIDTH = 5;
const BINS = 100 / BIN_WIDTH;

export function ScoreDistribution({ rankings }: Props) {
  const { t } = useI18n();
  const navigate = useNavigate();

  const data = useMemo(() => {
    const histogram = Array.from({ length: BINS }, (_, i) => ({
      label: (i * BIN_WIDTH).toFixed(0),
      min: i * BIN_WIDTH,
      max: (i + 1) * BIN_WIDTH,
      count: 0,
    }));

    rankings.forEach(({ composite_score: score }) => {
      if (score == null || isNaN(score)) return;
      const idx = Math.min(Math.max(0, Math.floor(score / BIN_WIDTH)), BINS - 1);
      histogram[idx].count++;
    });

    return histogram;
  }, [rankings]);

  const handleClick = useCallback((entry: (typeof data)[number]) => {
    if (entry.count > 0) {
      navigate(`/screener?minScore=${entry.min}&maxScore=${entry.max}`);
    }
  }, [navigate]);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.scoreDistribution')}</h2>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} className="cursor-pointer">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" onClick={(_d, idx) => handleClick(data[idx])}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.count > 0 ? '#3b82f6' : '#d1d5db'} className={entry.count > 0 ? 'cursor-pointer' : ''} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
