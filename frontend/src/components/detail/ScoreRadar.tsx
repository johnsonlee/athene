import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts';
import type { RankedStock } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  ranking: RankedStock | null;
}

export function ScoreRadar({ ranking }: Props) {
  const { t } = useI18n();
  if (!ranking) return null;

  const data = [
    { factor: t('factor.value'), score: ranking.value_score ?? 0 },
    { factor: t('factor.quality'), score: ranking.quality_score ?? 0 },
    { factor: t('factor.growth'), score: ranking.growth_score ?? 0 },
    { factor: t('factor.safety'), score: ranking.safety_score ?? 0 },
    { factor: t('factor.trend'), score: ranking.trend_score ?? 0 },
    { factor: t('factor.momentum'), score: ranking.momentum_score ?? 0 },
    { factor: t('factor.volatility'), score: ranking.volatility_score ?? 0 },
    { factor: t('factor.volume'), score: ranking.volume_score ?? 0 },
  ];

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
      <h3 className="mb-2 font-semibold text-gray-900 dark:text-white">{t('detail.factorScores')}</h3>
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
