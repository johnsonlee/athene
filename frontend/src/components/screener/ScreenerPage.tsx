import { useSearchParams } from 'react-router-dom';
import { useRankings } from '../../hooks/useRankings';
import { useFilterSort } from '../../hooks/useFilterSort';
import { useI18n } from '../../lib/i18n';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ScreenerTable } from './ScreenerTable';
import { FilterPanel } from './FilterPanel';
import { ExportButton } from './ExportButton';

export function ScreenerPage() {
  const [searchParams] = useSearchParams();
  const { data: rankings, loading, error } = useRankings();
  const minScoreParam = searchParams.get('minScore');
  const maxScoreParam = searchParams.get('maxScore');
  const { filtered, filter, setFilter, sectors } = useFilterSort(rankings, {
    sector: searchParams.get('sector') || undefined,
    tier: (searchParams.get('tier') as import('../../types').TierKey) || undefined,
    minScore: minScoreParam ? Number(minScoreParam) : undefined,
    maxScore: maxScoreParam ? Number(maxScoreParam) : undefined,
  });
  const { t } = useI18n();

  if (loading) return <LoadingSpinner message={t('common.loading')} />;
  if (error) return <p className="text-center text-red-600 dark:text-red-400">{t('common.error', { message: error })}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('screener.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('screener.showing', { filtered: filtered.length, total: rankings.length })}
          </p>
        </div>
        <ExportButton data={filtered} />
      </div>

      <FilterPanel
        filter={filter}
        onChange={setFilter}
        sectors={sectors}
      />

      <ScreenerTable data={filtered} />
    </div>
  );
}
