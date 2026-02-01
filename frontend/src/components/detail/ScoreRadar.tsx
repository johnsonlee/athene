import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts';
import type { FundamentalData, TechnicalData } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  fundamental: FundamentalData | null;
  technical: TechnicalData | null;
}

export function ScoreRadar({ fundamental, technical }: Props) {
  const { t } = useI18n();
  if (!fundamental && !technical) return null;

  const data = [
    { factor: t('factor.value'), score: fundamental?.value_score ?? 0 },
    { factor: t('factor.quality'), score: fundamental?.quality_score ?? 0 },
    { factor: t('factor.growth'), score: fundamental?.growth_score ?? 0 },
    { factor: t('factor.safety'), score: fundamental?.safety_score ?? 0 },
    { factor: t('factor.trend'), score: technical?.trend_score ?? 0 },
    { factor: t('factor.momentum'), score: technical?.momentum_score ?? 0 },
    { factor: t('factor.volatility'), score: technical?.volatility_score ?? 0 },
    { factor: t('factor.volume'), score: technical?.volume_score ?? 0 },
  ];

  // Don't render if all scores are 0 (no data)
  if (data.every((d) => d.score === 0)) return null;

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
