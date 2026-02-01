import { useMemo } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  ComposedChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { PriceBar, TechnicalData } from '../../types';
import { computeIndicators } from '../../lib/indicators';
import { formatLargeNumber } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

interface Props {
  prices: PriceBar[];
  technical: TechnicalData | null;
}

export function IndicatorCharts({ prices, technical }: Props) {
  const { t } = useI18n();
  const data = useMemo(() => {
    if (prices.length === 0) return [];
    const all = computeIndicators(prices);
    // Use last 60 bars for sub-charts
    return all.slice(-60).map((d) => ({
      ...d,
      date: d.date.slice(5), // MM-DD
    }));
  }, [prices]);

  if (data.length === 0) return null;

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* Volume chart */}
      <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">{t('detail.volume')}</h3>
        <ResponsiveContainer width="100%" height={150}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis tickFormatter={formatLargeNumber} tick={{ fontSize: 10 }} width={50} />
            <Tooltip formatter={(value?: number) => [formatLargeNumber(value ?? 0), t('detail.volume')]} />
            <Bar dataKey="volume" fill="#94a3b8" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* RSI chart */}
      <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          {t('chart.rsi14')}
          {technical?.rsi != null && (
            <span className="ml-2 font-mono text-xs text-gray-500 dark:text-gray-400">{technical.rsi.toFixed(1)}</span>
          )}
        </h3>
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} ticks={[30, 50, 70]} tick={{ fontSize: 10 }} width={30} />
            <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={30} stroke="#16a34a" strokeDasharray="3 3" />
            <Tooltip formatter={(value?: number) => [value != null ? value.toFixed(1) : 'N/A', 'RSI']} />
            <Line dataKey="rsi" stroke="#8b5cf6" dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* MACD chart */}
      <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          {t('chart.macd1226')}
          {technical?.macd_histogram != null && (
            <span className={`ml-2 font-mono text-xs ${technical.macd_histogram >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {t('chart.hist')}: {technical.macd_histogram.toFixed(3)}
            </span>
          )}
        </h3>
        <ResponsiveContainer width="100%" height={150}>
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 10 }} width={50} />
            <ReferenceLine y={0} stroke="#9ca3af" />
            <Tooltip formatter={(value?: number, name?: string) => [
              value != null ? value.toFixed(3) : 'N/A',
              name === 'macdLine' ? t('metric.macd') : name === 'macdSignal' ? t('chart.signal') : t('chart.histogram'),
            ]} />
            <Bar dataKey="macdHist" fill="#94a3b8" opacity={0.5} />
            <Line dataKey="macdLine" stroke="#3b82f6" dot={false} connectNulls strokeWidth={1.5} />
            <Line dataKey="macdSignal" stroke="#f97316" dot={false} connectNulls strokeWidth={1.5} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Stochastic chart */}
      <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <h3 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
          {t('chart.stochastic')}
          {technical?.stoch_k != null && (
            <span className="ml-2 font-mono text-xs text-gray-500 dark:text-gray-400">
              K: {technical.stoch_k.toFixed(1)} / D: {technical.stoch_d?.toFixed(1) ?? 'N/A'}
            </span>
          )}
        </h3>
        <ResponsiveContainer width="100%" height={150}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} ticks={[20, 50, 80]} tick={{ fontSize: 10 }} width={30} />
            <ReferenceLine y={80} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={20} stroke="#16a34a" strokeDasharray="3 3" />
            <Tooltip formatter={(value?: number, name?: string) => [
              value != null ? value.toFixed(1) : 'N/A',
              name === 'stochK' ? '%K' : '%D',
            ]} />
            <Line dataKey="stochK" stroke="#3b82f6" dot={false} connectNulls strokeWidth={1.5} />
            <Line dataKey="stochD" stroke="#f97316" dot={false} connectNulls strokeWidth={1.5} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
