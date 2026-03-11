import { useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { RankedStock } from '../../types';
import { useI18n } from '../../lib/i18n';
import { useTheme } from '../../lib/theme';

interface Props {
  rankings: RankedStock[];
}

const BIN_WIDTH = 5;
const BINS = 100 / BIN_WIDTH;

export function ScoreDistribution({ rankings }: Props) {
  const { t } = useI18n();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const isDark = theme === 'dark';

  const data = useMemo(() => {
    const histogram = Array.from({ length: BINS }, (_, i) => ({
      label: (i * BIN_WIDTH).toFixed(0),
      min: i * BIN_WIDTH,
      max: (i + 1) * BIN_WIDTH,
      count: 0,
    }));

    rankings.forEach((r) => {
      const score = r.alpha_score ?? r.composite_score;
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

  const barFill = isDark ? '#06b6d4' : '#3b82f6';
  const barEmpty = isDark ? '#1e293b' : '#d1d5db';
  const gridColor = isDark ? 'rgba(6,182,212,0.08)' : '#e5e7eb';
  const axisColor = isDark ? '#475569' : '#9ca3af';

  return (
    <div className="tech-card p-4">
      <h2 className="tech-heading mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.scoreDistribution')}</h2>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} className="cursor-pointer">
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: axisColor }} interval="preserveStartEnd" />
          <YAxis tick={{ fill: axisColor }} />
          <Tooltip
            contentStyle={{
              background: isDark ? 'rgba(15,23,42,0.9)' : '#fff',
              border: isDark ? '1px solid rgba(6,182,212,0.2)' : '1px solid #e5e7eb',
              borderRadius: '8px',
              color: isDark ? '#e2e8f0' : '#1f2937',
              backdropFilter: 'blur(8px)',
            }}
          />
          <Bar dataKey="count" onClick={(_d, idx) => handleClick(data[idx])} radius={[2, 2, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.count > 0 ? barFill : barEmpty} className={entry.count > 0 ? 'cursor-pointer' : ''} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
