import { useI18n } from '../../lib/i18n';
import { formatLargeNumber } from '../../lib/formatters';
import type { CompanyProfile as ProfileData, FundamentalData, RankedStock } from '../../types';

interface Props {
  profile: ProfileData | null;
  fundamental: FundamentalData | null;
  ranking: RankedStock | null;
}

/* ── Margin waterfall bar ── */
function MarginBar({ label, value, maxValue }: { label: string; value: number; maxValue: number }) {
  const pct = (value * 100);
  const width = Math.max(0, Math.min(100, (pct / maxValue) * 100));
  const isNegative = pct < 0;

  return (
    <div className="flex items-center gap-2">
      <span className="w-16 shrink-0 text-right text-xs text-gray-500 dark:text-gray-500">{label}</span>
      <div className="relative h-5 flex-1 overflow-hidden rounded bg-gray-100 dark:bg-slate-800">
        <div
          className={`absolute inset-y-0 left-0 rounded transition-all ${isNegative ? 'bg-red-400/60 dark:bg-red-500/40' : 'bg-blue-400/60 dark:bg-cyan-500/40'}`}
          style={{ width: `${Math.abs(width)}%` }}
        />
        <span className="relative z-10 flex h-full items-center px-2 text-xs font-mono font-medium text-gray-700 dark:text-gray-300">
          {pct.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

export function CompanyProfile({ profile, fundamental, ranking }: Props) {
  const { t, tIndustry } = useI18n();

  const hasDescription = !!profile?.longBusinessSummary;
  const hasMargins = fundamental &&
    (fundamental.gross_margin != null || fundamental.operating_margin != null || fundamental.profit_margin != null);

  if (!hasDescription && !hasMargins) return null;

  // For scaling the margin bars — use gross margin as max, fallback to 100%
  const maxMarginPct = fundamental?.gross_margin
    ? Math.max(fundamental.gross_margin * 100, 10)
    : 100;

  return (
    <div className="tech-card space-y-4 p-4">
      {/* Company description */}
      {hasDescription && (
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-500">
            {ranking?.sector && (
              <span>{t(`sector.${ranking.sector}` as any) || ranking.sector}</span>
            )}
            {ranking?.sector && ranking?.industry && (
              <span className="text-gray-300 dark:text-gray-700">&middot;</span>
            )}
            {ranking?.industry && (
              <span>{tIndustry(ranking.industry)}</span>
            )}
            {profile?.fullTimeEmployees && (
              <>
                <span className="text-gray-300 dark:text-gray-700">&middot;</span>
                <span>{t('profile.employees')}: {profile.fullTimeEmployees.toLocaleString()}</span>
              </>
            )}
            {fundamental?.market_cap && (
              <>
                <span className="text-gray-300 dark:text-gray-700">&middot;</span>
                <span>{t('profile.marketCap')}: ${formatLargeNumber(fundamental.market_cap)}</span>
              </>
            )}
          </div>
          <p className="text-sm leading-relaxed text-gray-600 dark:text-gray-400">
            {profile!.longBusinessSummary}
          </p>
        </div>
      )}

      {/* Margin waterfall */}
      {hasMargins && (
        <div>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-500">
            {t('profile.marginBreakdown')}
          </h3>
          <div className="space-y-1.5">
            {fundamental!.gross_margin != null && (
              <MarginBar label={t('profile.grossMargin')} value={fundamental!.gross_margin} maxValue={maxMarginPct} />
            )}
            {fundamental!.operating_margin != null && (
              <MarginBar label={t('profile.operatingMargin')} value={fundamental!.operating_margin} maxValue={maxMarginPct} />
            )}
            {fundamental!.profit_margin != null && (
              <MarginBar label={t('profile.profitMargin')} value={fundamental!.profit_margin} maxValue={maxMarginPct} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
