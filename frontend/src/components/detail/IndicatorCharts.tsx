import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { PriceBar, TechnicalData } from '../../types';

interface Props {
  prices: PriceBar[];
  technical: TechnicalData | null;
}

export function IndicatorCharts({ prices, technical }: Props) {
  if (prices.length === 0) return null;

  // Use last 60 bars for sub-charts
  const recent = prices.slice(-60);

  const priceData = recent.map((p) => ({
    date: p.date.slice(5), // MM-DD
    close: p.close,
    volume: p.volume,
  }));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* RSI chart */}
      {technical?.rsi != null && (
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-gray-700">RSI ({technical.rsi.toFixed(1)})</h3>
          <ResponsiveContainer width="100%" height={150}>
            <LineChart data={priceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis domain={[0, 100]} ticks={[30, 50, 70]} />
              <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
              <ReferenceLine y={30} stroke="#16a34a" strokeDasharray="3 3" />
              <Tooltip />
              <Line dataKey="close" stroke="#3b82f6" dot={false} name="Price" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Volume chart */}
      <div className="rounded-lg bg-white p-4 shadow-sm">
        <h3 className="mb-2 text-sm font-semibold text-gray-700">Volume</h3>
        <ResponsiveContainer width="100%" height={150}>
          <BarChart data={priceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="volume" fill="#94a3b8" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
