import { useRankings } from '../../hooks/useRankings';
import { useMeta } from '../../hooks/useMeta';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { TopMovers } from './TopMovers';
import { SectorHeatmap } from './SectorHeatmap';
import { ScoreDistribution } from './ScoreDistribution';

export function Dashboard() {
  const { data: rankings, loading, error } = useRankings();
  const { data: meta } = useMeta();

  if (loading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error) return <p className="text-center text-red-600">Error: {error}</p>;

  const tierCounts = rankings.reduce<Record<string, number>>((acc, s) => {
    acc[s.tier_label] = (acc[s.tier_label] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Market Overview</h1>
        {meta && (
          <p className="mt-1 text-sm text-gray-500">
            {meta.ticker_count} stocks analyzed &middot; {meta.date}
          </p>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        {Object.entries(tierCounts).map(([label, count]) => (
          <div key={label} className="rounded-lg bg-white p-4 shadow-sm">
            <p className="text-sm text-gray-500">{label}</p>
            <p className="text-2xl font-bold text-gray-900">{count}</p>
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
