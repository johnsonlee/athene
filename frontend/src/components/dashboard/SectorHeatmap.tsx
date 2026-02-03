import { useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';
import type { RankedStock } from '../../types';
import { formatScore, formatLargeNumber } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';
import { useTheme } from '../../lib/theme';

interface Props {
  rankings: RankedStock[];
}

interface SectorNode {
  name: string;
  displayName: string;
  size: number;
  avgScore: number;
  count: number;
  marketCap: number;
  [key: string]: unknown;
}

function scoreToColor(score: number, isDark: boolean): string {
  if (isDark) {
    if (score >= 65) return '#059669'; // emerald-600
    if (score >= 55) return '#0d9488'; // teal-600
    if (score >= 45) return '#475569'; // slate-600
    if (score >= 35) return '#c2410c'; // orange-700
    return '#b91c1c'; // red-700
  }
  if (score >= 65) return '#16a34a';
  if (score >= 55) return '#4ade80';
  if (score >= 45) return '#9ca3af';
  if (score >= 35) return '#fb923c';
  return '#ef4444';
}

function truncateLabel(text: string | undefined, width: number, fontSize: number): string {
  if (!text) return '';
  const charWidth = fontSize * 0.62;
  const maxChars = Math.floor((width - 10) / charWidth);
  if (maxChars < 2) return '';
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars - 1) + '\u2026';
}

function CustomContent(props: any) {
  const { x, y, width, height, displayName, name, avgScore, count, isDark } = props;
  if (!width || !height || width < 30 || height < 20) return null;

  const fill = scoreToColor(avgScore, isDark);
  const showScore = width > 50 && height > 35;
  const showCount = width > 60 && height > 50;
  const fontSize = width > 100 ? 12 : width > 60 ? 10 : 9;
  const label = truncateLabel(displayName || name, width, fontSize);
  const clipId = `sc-${Math.round(x)}-${Math.round(y)}`;
  const strokeColor = isDark ? 'rgba(6,182,212,0.15)' : '#fff';

  return (
    <g>
      <defs>
        <clipPath id={clipId}>
          <rect x={x + 1} y={y + 1} width={width - 2} height={height - 2} />
        </clipPath>
      </defs>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke={strokeColor} strokeWidth={isDark ? 1 : 2}
        rx={4} opacity={isDark ? 0.9 : 0.85} className="cursor-pointer hover:opacity-100 transition-opacity" />
      <g clipPath={`url(#${clipId})`}>
        {label && (
          <text x={x + width / 2} y={y + height / 2 - (showScore ? 8 : 0)} textAnchor="middle" dominantBaseline="central"
            fill="#fff" fontSize={fontSize} fontWeight="600">
            {label}
          </text>
        )}
        {showScore && (
          <text x={x + width / 2} y={y + height / 2 + 10} textAnchor="middle" dominantBaseline="central"
            fill="rgba(255,255,255,0.85)" fontSize={10} fontFamily="monospace">
            {formatScore(avgScore)}
          </text>
        )}
        {showCount && (
          <text x={x + width / 2} y={y + height / 2 + 24} textAnchor="middle" dominantBaseline="central"
            fill="rgba(255,255,255,0.65)" fontSize={9}>
            {count}
          </text>
        )}
      </g>
    </g>
  );
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload as SectorNode;
  return (
    <div className="tech-card rounded-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-900 dark:text-white">{d.displayName || d.name}</p>
      <p className="text-gray-600 dark:text-gray-400">Score: <span className="font-mono">{formatScore(d.avgScore)}</span></p>
      <p className="text-gray-600 dark:text-gray-400">Market Cap: <span className="font-mono">{formatLargeNumber(d.marketCap)}</span></p>
      <p className="text-gray-600 dark:text-gray-400">{d.count} stocks</p>
    </div>
  );
}

export function SectorHeatmap({ rankings }: Props) {
  const { t } = useI18n();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const isDark = theme === 'dark';

  const data = useMemo(() => {
    const grouped = new Map<string, { totalScore: number; totalCap: number; count: number }>();
    rankings.forEach((s) => {
      if (!s.sector || s.sector === 'Unknown') return;
      const entry = grouped.get(s.sector) || { totalScore: 0, totalCap: 0, count: 0 };
      entry.totalScore += s.composite_score;
      entry.totalCap += s.market_cap ?? 0;
      entry.count += 1;
      grouped.set(s.sector, entry);
    });
    return Array.from(grouped.entries())
      .map(([name, { totalScore, totalCap, count }]): SectorNode => ({
        name,
        displayName: t(`sector.${name}` as any) || name,
        size: totalCap || count,
        avgScore: totalScore / count,
        count,
        marketCap: totalCap,
      }))
      .sort((a, b) => b.size - a.size);
  }, [rankings, t]);

  const handleClick = useCallback((node: any) => {
    if (node?.name) navigate(`/screener?sector=${encodeURIComponent(node.name)}`);
  }, [navigate]);

  return (
    <div className="tech-card p-4 lg:col-span-2">
      <h2 className="tech-heading mb-3 text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.sectorOverview')}</h2>
      <ResponsiveContainer width="100%" height={320}>
        <Treemap
          data={data}
          dataKey="size"
          aspectRatio={4 / 3}
          content={<CustomContent isDark={isDark} />}
          onClick={handleClick}
        >
          <Tooltip content={<CustomTooltip />} />
        </Treemap>
      </ResponsiveContainer>
    </div>
  );
}
