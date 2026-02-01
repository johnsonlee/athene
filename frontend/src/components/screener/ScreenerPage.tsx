import { useRankings } from '../../hooks/useRankings';
import { useFilterSort } from '../../hooks/useFilterSort';
import { useI18n } from '../../lib/i18n';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ScreenerTable } from './ScreenerTable';
import { FilterPanel } from './FilterPanel';
import { ExportButton } from './ExportButton';

export function ScreenerPage() {
  const { data: rankings, loading, error } = useRankings();
  const { filtered, filter, setFilter, sectors } = useFilterSort(rankings);
  const { t } = useI18n();

  if (loading) return <LoadingSpinner message={t('common.loading')} />;
  if (error) return <p className="text-center text-red-600">{t('common.error', { message: error })}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('screener.title')}</h1>
          <p className="text-sm text-gray-500">
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
