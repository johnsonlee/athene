import { useRankings } from '../../hooks/useRankings';
import { useFilterSort } from '../../hooks/useFilterSort';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ScreenerTable } from './ScreenerTable';
import { FilterPanel } from './FilterPanel';
import { ExportButton } from './ExportButton';

export function ScreenerPage() {
  const { data: rankings, loading, error } = useRankings();
  const { filtered, filter, setFilter, sectors } = useFilterSort(rankings);

  if (loading) return <LoadingSpinner message="Loading screener data..." />;
  if (error) return <p className="text-center text-red-600">Error: {error}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Stock Screener</h1>
          <p className="text-sm text-gray-500">
            {filtered.length} of {rankings.length} stocks
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
