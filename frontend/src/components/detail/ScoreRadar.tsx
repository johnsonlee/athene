import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts';
import type { RankedStock } from '../../types';

interface Props {
  ranking: RankedStock | null;
}

export function ScoreRadar({ ranking }: Props) {
  if (!ranking) return null;

  const data = [
    { factor: 'Value', score: ranking.value_score ?? 0 },
    { factor: 'Quality', score: ranking.quality_score ?? 0 },
    { factor: 'Growth', score: ranking.growth_score ?? 0 },
    { factor: 'Safety', score: ranking.safety_score ?? 0 },
    { factor: 'Trend', score: ranking.trend_score ?? 0 },
    { factor: 'Momentum', score: ranking.momentum_score ?? 0 },
    { factor: 'Volatility', score: ranking.volatility_score ?? 0 },
    { factor: 'Volume', score: ranking.volume_score ?? 0 },
  ];

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <h3 className="mb-2 font-semibold text-gray-900">Factor Scores</h3>
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="factor" tick={{ fontSize: 11 }} />
          <PolarRadiusAxis tick={{ fontSize: 10 }} />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.3}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
