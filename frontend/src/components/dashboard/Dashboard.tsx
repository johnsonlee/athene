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

  const scoreBuckets = [
    { key: '50+', label: 'Alpha ≥ 50', min: 50, max: Infinity },
    { key: '30-50', label: '30–50', min: 30, max: 50 },
    { key: '20-30', label: '20–30', min: 20, max: 30 },
    { key: '10-20', label: '10–20', min: 10, max: 20 },
    { key: '0-10', label: '< 10', min: 0, max: 10 },
  ];
  const bucketCounts = scoreBuckets.map((b) => ({
    ...b,
    count: rankings.filter((s) => {
      const score = s.alpha_score ?? s.composite_score ?? 0;
      return score >= b.min && score < b.max;
    }).length,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="tech-heading text-xl font-bold tracking-tight text-gray-900 sm:text-2xl dark:text-white">{t('dashboard.title')}</h1>
        {meta && (
          <p className="mt-1 font-mono text-sm text-gray-500 dark:text-gray-500">
            {t('dashboard.analyzed', { count: meta.ticker_count })} &middot; {meta.timestamp?.slice(0, 16).replace('T', ' ') || meta.date}
          </p>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5 sm:gap-4">
        {bucketCounts.map((b) => (
          <div key={b.key}
            className="tech-card cursor-pointer p-3 transition-all hover:scale-[1.02] active:scale-[0.98] sm:p-4"
            onClick={() => navigate(`/screener?minScore=${b.min}&maxScore=${b.max === Infinity ? 100 : b.max}`)}
          >
            <p className="text-xs text-gray-500 sm:text-sm dark:text-gray-500">{b.label}</p>
            <p className="font-mono text-xl font-bold text-gray-900 sm:text-2xl dark:text-white">{b.count}</p>
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
