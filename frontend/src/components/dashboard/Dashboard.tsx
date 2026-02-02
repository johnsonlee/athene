import { useNavigate } from 'react-router-dom';
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
  const navigate = useNavigate();

  if (loading) return <LoadingSpinner message={t('common.loading')} />;
  if (error) return <p className="text-center text-red-600 dark:text-red-400">{t('common.error', { message: error })}</p>;

  const tierCounts = rankings.reduce<Record<string, { label: string; count: number }>>((acc, s) => {
    if (!acc[s.tier]) acc[s.tier] = { label: t(`tier.${s.tier}` as any), count: 0 };
    acc[s.tier].count += 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('dashboard.title')}</h1>
        {meta && (
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {t('dashboard.analyzed', { count: meta.ticker_count })} &middot; {meta.timestamp?.slice(0, 16).replace('T', ' ') || meta.date}
          </p>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        {Object.entries(tierCounts).map(([tier, { label, count }]) => (
          <div key={tier}
            className="cursor-pointer rounded-lg bg-white p-4 shadow-sm transition-opacity hover:opacity-80 dark:bg-gray-800"
            onClick={() => navigate(`/screener?tier=${tier}`)}
          >
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
