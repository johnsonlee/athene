import type { MacroRegime } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  macro: MacroRegime;
}

export function RegimeBanner({ macro }: Props) {
  const { t } = useI18n();

  const regimeLabel =
    macro.regime === 'risk_on'
      ? t('trends.regimeRiskOn')
      : macro.regime === 'risk_off'
        ? t('trends.regimeRiskOff')
        : t('trends.regimeNeutral');

  const regimeColor =
    macro.regime === 'risk_on'
      ? 'border-green-500/30 bg-green-50 dark:bg-green-500/10'
      : macro.regime === 'risk_off'
        ? 'border-red-500/30 bg-red-50 dark:bg-red-500/10'
        : 'border-gray-300 bg-gray-50 dark:border-gray-600 dark:bg-gray-800';

  const dotColor =
    macro.regime === 'risk_on'
      ? 'bg-green-500'
      : macro.regime === 'risk_off'
        ? 'bg-red-500'
        : 'bg-gray-400';

  const formatPct = (v: number | null) => (v != null ? `${(v * 100).toFixed(1)}%` : '—');

  return (
    <div className={`flex flex-wrap items-center gap-x-5 gap-y-2 rounded-lg border px-4 py-2.5 ${regimeColor}`}>
      <div className="flex items-center gap-2">
        <span className={`inline-block h-2.5 w-2.5 rounded-full ${dotColor}`} />
        <span className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('trends.regime')}: {regimeLabel}
        </span>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-gray-600 dark:text-gray-400">
        {macro.vix != null && (
          <span>{t('trends.vix')}: {macro.vix.toFixed(1)}</span>
        )}
        {macro.sp500_vs_sma200_pct != null && (
          <span>S&P vs SMA200: {formatPct(macro.sp500_vs_sma200_pct)}</span>
        )}
        {macro.yield_curve_spread != null && (
          <span>{t('trends.yieldCurve')}: {macro.yield_curve_spread > 0 ? '+' : ''}{macro.yield_curve_spread.toFixed(2)}pp</span>
        )}
      </div>
    </div>
  );
}
