import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import type { RankedStock } from '../../types';
import { formatScore } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

interface Props {
  rankings: RankedStock[];
}

export function SectorHeatmap({ rankings }: Props) {
  const { t } = useI18n();
  const navigate = useNavigate();

  const sectorData = useMemo(() => {
    const grouped = new Map<string, { total: number; count: number }>();
    rankings.forEach((s) => {
      if (!s.sector || s.sector === 'Unknown') return;
      const sector = s.sector;
      const entry = grouped.get(sector) || { total: 0, count: 0 };
      entry.total += s.composite_score;
      entry.count += 1;
      grouped.set(sector, entry);
    });
    return Array.from(grouped.entries())
      .map(([sector, { total, count }]) => ({
        sector,
        avgScore: total / count,
        count,
      }))
      .sort((a, b) => b.avgScore - a.avgScore);
  }, [rankings]);

  const maxScore = Math.max(...sectorData.map((d) => Math.abs(d.avgScore)), 0.01);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm lg:col-span-2 dark:bg-gray-800">
      <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.sectorOverview')}</h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {sectorData.map(({ sector, avgScore, count }) => {
          const intensity = avgScore / maxScore; // -1 to 1
          const bg =
            intensity > 0
              ? `rgba(22, 163, 74, ${Math.min(intensity, 1) * 0.5})`
              : `rgba(239, 68, 68, ${Math.min(Math.abs(intensity), 1) * 0.5})`;
          return (
            <div
              key={sector}
              className="cursor-pointer rounded p-3 text-center transition-opacity hover:opacity-80"
              style={{ backgroundColor: bg }}
              onClick={() => navigate(`/screener?sector=${encodeURIComponent(sector)}`)}
            >
              <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{sector}</p>
              <p className="text-lg font-bold text-gray-900 dark:text-white">{formatScore(avgScore)}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{t('dashboard.stocks', { count })}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
