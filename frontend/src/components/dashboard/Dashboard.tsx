import { useRankings } from '../../hooks/useRankings';
import { useMeta } from '../../hooks/useMeta';
import { useI18n } from '../../lib/i18n';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { TopMovers } from './TopMovers';
import { SectorHeatmap } from './SectorHeatmap';
import { ScoreDistribution } from './ScoreDistribution';

export function Dashboard() {
  const { data: rankings, loading, error } = useRankings();
  const { data: meta } = useMeta();
  const { t } = useI18n();

  if (loading) return <LoadingSpinner message={t('common.loading')} />;
  if (error) return <p className="text-center text-red-600 dark:text-red-400">{t('common.error', { message: error })}</p>;

  const tierCounts = rankings.reduce<Record<string, number>>((acc, s) => {
    const label = t(`tier.${s.tier}` as any);
    acc[label] = (acc[label] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('dashboard.title')}</h1>
        {meta && (
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {t('dashboard.analyzed', { count: meta.ticker_count })} &middot; {meta.date}
          </p>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        {Object.entries(tierCounts).map(([label, count]) => (
          <div key={label} className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
            <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{count}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <TopMovers rankings={rankings} />
        <SectorHeatmap rankings={rankings} />
      </div>

      <ScoreDistribution rankings={rankings} />
    </div>
  );
}
