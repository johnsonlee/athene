import { useParams, Link } from 'react-router-dom';
import { useStockDetail } from '../../hooks/useStockDetail';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ScoreBadge } from '../common/ScoreBadge';
import { PriceChart } from './PriceChart';
import { IndicatorCharts } from './IndicatorCharts';
import { ScoreRadar } from './ScoreRadar';
import { formatScore, formatPrice, formatPercent, formatLargeNumber, formatRatio } from '../../lib/formatters';

export function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const { data, loading, error } = useStockDetail(ticker);

  if (loading) return <LoadingSpinner message={`Loading ${ticker}...`} />;
  if (error) return <p className="text-center text-red-600">Error: {error}</p>;
  if (!data) return <p className="text-center text-gray-500">No data found</p>;

  const { fundamental, technical, sentiment, ranking } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/screener" className="text-sm text-blue-600 hover:underline">&larr; Back to Screener</Link>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">{ticker}</h1>
          {fundamental?.current_price && (
            <p className="text-xl font-semibold text-gray-700">
              {formatPrice(fundamental.current_price)}
            </p>
          )}
        </div>
        {ranking && (
          <div className="text-right">
            <p className="text-sm text-gray-500">Rank #{ranking.rank}</p>
            <p className="text-lg font-bold">{formatScore(ranking.composite_score)}</p>
            <ScoreBadge tier={ranking.tier} label={ranking.tier_label} />
          </div>
        )}
      </div>

      {/* Price Chart */}
      <PriceChart prices={data.prices} ticker={ticker!} />

      {/* Indicator Sub-charts */}
      <IndicatorCharts prices={data.prices} technical={technical} />

      {/* Score Radar + Cards */}
      <div className="grid gap-6 lg:grid-cols-3">
        <ScoreRadar ranking={ranking} />

        {/* Fundamental card */}
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <h3 className="mb-3 font-semibold text-gray-900">Fundamentals</h3>
          {fundamental ? (
            <dl className="space-y-1 text-sm">
              <MetricRow label="P/E" value={formatRatio(fundamental.pe)} />
              <MetricRow label="Fwd P/E" value={formatRatio(fundamental.forward_pe)} />
              <MetricRow label="P/B" value={formatRatio(fundamental.pb)} />
              <MetricRow label="P/S" value={formatRatio(fundamental.ps)} />
              <MetricRow label="ROE" value={formatPercent(fundamental.roe)} />
              <MetricRow label="ROA" value={formatPercent(fundamental.roa)} />
              <MetricRow label="Rev Growth" value={formatPercent(fundamental.revenue_growth)} />
              <MetricRow label="Earn Growth" value={formatPercent(fundamental.earnings_growth)} />
              <MetricRow label="Debt/Equity" value={formatRatio(fundamental.debt_to_equity)} />
              <MetricRow label="Market Cap" value={formatLargeNumber(fundamental.market_cap)} />
              <MetricRow label="Profit Margin" value={formatPercent(fundamental.profit_margin)} />
              <MetricRow label="Dividend Yield" value={formatPercent(fundamental.dividend_yield)} />
              <MetricRow label="Beta" value={formatRatio(fundamental.beta)} />
              <MetricRow label="52W High" value={formatPrice(fundamental.high_52w)} />
              <MetricRow label="52W Low" value={formatPrice(fundamental.low_52w)} />
            </dl>
          ) : (
            <p className="text-sm text-gray-400">No data available</p>
          )}
        </div>

        {/* Sentiment + Technical card */}
        <div className="space-y-4">
          <div className="rounded-lg bg-white p-4 shadow-sm">
            <h3 className="mb-3 font-semibold text-gray-900">Technical</h3>
            {technical ? (
              <dl className="space-y-1 text-sm">
                <MetricRow label="RSI" value={formatRatio(technical.rsi)} />
                <MetricRow label="MACD" value={formatRatio(technical.macd_line)} />
                <MetricRow label="MACD Hist" value={formatRatio(technical.macd_histogram)} />
                <MetricRow label="SMA 20" value={formatPrice(technical.sma_20)} />
                <MetricRow label="SMA 50" value={formatPrice(technical.sma_50)} />
                <MetricRow label="SMA 200" value={formatPrice(technical.sma_200)} />
                <MetricRow label="BB Position" value={formatRatio(technical.bb_position)} />
                <MetricRow label="Vol Ratio" value={formatRatio(technical.volume_ratio)} />
                <MetricRow label="Stoch K" value={formatRatio(technical.stoch_k)} />
                <MetricRow label="Stoch D" value={formatRatio(technical.stoch_d)} />
              </dl>
            ) : (
              <p className="text-sm text-gray-400">No data available</p>
            )}
          </div>

          <div className="rounded-lg bg-white p-4 shadow-sm">
            <h3 className="mb-3 font-semibold text-gray-900">Sentiment</h3>
            {sentiment ? (
              <dl className="space-y-1 text-sm">
                <MetricRow label="Compound" value={formatRatio(sentiment.sentiment_compound)} />
                <MetricRow label="Positive" value={formatPercent(sentiment.sentiment_pos)} />
                <MetricRow label="Negative" value={formatPercent(sentiment.sentiment_neg)} />
                <MetricRow label="Neutral" value={formatPercent(sentiment.sentiment_neu)} />
                <MetricRow label="News Count" value={String(sentiment.news_count)} />
              </dl>
            ) : (
              <p className="text-sm text-gray-400">No data available</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-gray-500">{label}</dt>
      <dd className="font-mono font-medium text-gray-900">{value}</dd>
    </div>
  );
}
