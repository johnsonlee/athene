import { useI18n } from '../../lib/i18n';
import { formatPercent, formatRatio } from '../../lib/formatters';
import type { AnalystData } from '../../types';

interface Props {
  analyst: AnalystData | null;
}

function ratingLabel(rating: number, t: (key: any) => string): string {
  if (rating <= 1.5) return t('analyst.strongBuy');
  if (rating <= 2.5) return t('analyst.buy');
  if (rating <= 3.5) return t('analyst.hold');
  if (rating <= 4.5) return t('analyst.sell');
  return t('analyst.strongSell');
}

function ratingColor(rating: number): string {
  if (rating <= 1.5) return 'text-emerald-600 dark:text-emerald-400';
  if (rating <= 2.5) return 'text-green-600 dark:text-green-400';
  if (rating <= 3.5) return 'text-gray-600 dark:text-gray-400';
  if (rating <= 4.5) return 'text-orange-600 dark:text-orange-400';
  return 'text-red-600 dark:text-red-400';
}

function ConsensusGauge({ rating }: { rating: number }) {
  const { t } = useI18n();
  // rating: 1 = Strong Buy, 5 = Strong Sell
  const pct = ((rating - 1) / 4) * 100;
  const segments = [
    { color: 'bg-emerald-500', label: t('analyst.strongBuy') },
    { color: 'bg-green-400', label: t('analyst.buy') },
    { color: 'bg-gray-400 dark:bg-gray-500', label: t('analyst.hold') },
    { color: 'bg-orange-400', label: t('analyst.sell') },
    { color: 'bg-red-500', label: t('analyst.strongSell') },
  ];

  // Which segment is the rating in? (0-indexed)
  const activeIdx = Math.min(4, Math.floor((rating - 1) / 0.8));

  return (
    <div>
      {/* Rating label */}
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className={`text-sm font-semibold ${ratingColor(rating)}`}>
          {ratingLabel(rating, t)}
        </span>
        <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
          {formatRatio(rating)}
        </span>
      </div>

      {/* Segmented gauge */}
      <div className="relative h-3 flex gap-0.5 overflow-visible">
        {segments.map((seg, i) => (
          <div
            key={i}
            className={`flex-1 rounded-sm ${seg.color} ${i === activeIdx ? 'opacity-100' : 'opacity-30'}`}
          />
        ))}
        {/* Marker */}
        <div
          className="absolute -top-0.5 h-4 w-1 rounded-full bg-gray-900 dark:bg-white shadow"
          style={{ left: `${Math.max(1, Math.min(99, pct))}%`, transform: 'translateX(-50%)' }}
        />
      </div>

      {/* Scale labels */}
      <div className="mt-1 flex justify-between text-[9px] text-gray-400 dark:text-gray-500">
        <span>1</span>
        <span>2</span>
        <span>3</span>
        <span>4</span>
        <span>5</span>
      </div>
    </div>
  );
}

/** Upgrades vs downgrades distribution bar */
function RevisionBar({ upgrades, downgrades, t }: { upgrades: number; downgrades: number; t: (key: any) => string }) {
  const total = upgrades + downgrades;
  if (total === 0) return null;
  const upPct = (upgrades / total) * 100;
  const downPct = (downgrades / total) * 100;

  return (
    <div>
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">
        {t('analyst.revisions')}
      </p>
      <div className="flex h-3 overflow-hidden rounded-full">
        <div className="bg-green-500" style={{ width: `${upPct}%` }} />
        <div className="bg-red-500" style={{ width: `${downPct}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-[10px]">
        <span className="text-green-600 dark:text-green-400">
          {t('analyst.upgrades')} {upgrades}
        </span>
        <span className="text-red-600 dark:text-red-400">
          {t('analyst.downgrades')} {downgrades}
        </span>
      </div>
    </div>
  );
}

function MetricCell({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="py-1.5">
      <p className="text-[10px] text-gray-500 dark:text-gray-500 leading-tight">{label}</p>
      <p className={`font-mono text-sm font-medium leading-snug ${color || 'text-gray-900 dark:text-white'}`}>{value}</p>
    </div>
  );
}

export function AnalystConsensus({ analyst }: Props) {
  const { t } = useI18n();

  if (!analyst) {
    return (
      <div className="tech-card p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-500">
          {t('analyst.title')}
        </h3>
        <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">{t('analyst.noData')}</p>
      </div>
    );
  }

  const upsideColor = analyst.target_upside != null
    ? (analyst.target_upside > 0.1 ? 'text-green-600 dark:text-green-400'
      : analyst.target_upside < 0 ? 'text-red-600 dark:text-red-400'
        : 'text-gray-900 dark:text-white')
    : undefined;

  const momColor = analyst.revision_momentum != null
    ? (analyst.revision_momentum > 0.2 ? 'text-green-600 dark:text-green-400'
      : analyst.revision_momentum < -0.2 ? 'text-red-600 dark:text-red-400'
        : 'text-gray-900 dark:text-white')
    : undefined;

  const upgrades = analyst.analyst_upgrades ?? 0;
  const downgrades = analyst.analyst_downgrades ?? 0;

  return (
    <div className="tech-card space-y-3 p-4">
      <h2 className="tech-heading text-base font-semibold text-gray-900 sm:text-lg dark:text-white">
        {t('analyst.title')}
      </h2>

      {/* Consensus gauge with label */}
      {analyst.consensus_rating != null && (
        <ConsensusGauge rating={analyst.consensus_rating} />
      )}

      {/* Upgrades vs downgrades distribution */}
      {(upgrades > 0 || downgrades > 0) && (
        <RevisionBar upgrades={upgrades} downgrades={downgrades} t={t} />
      )}

      {/* Metric grid */}
      <div className="grid grid-cols-2 gap-x-4 sm:grid-cols-3">
        <MetricCell
          label={t('analyst.targetUpside')}
          value={formatPercent(analyst.target_upside)}
          color={upsideColor}
        />
        <MetricCell
          label={t('analyst.analysts')}
          value={analyst.analyst_count != null ? String(Math.round(analyst.analyst_count)) : 'N/A'}
        />
        <MetricCell
          label={t('analyst.revMomentum')}
          value={formatRatio(analyst.revision_momentum)}
          color={momColor}
        />
      </div>
    </div>
  );
}
