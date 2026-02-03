import type { RankedStock } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  data: RankedStock[];
}

export function ExportButton({ data }: Props) {
  const { t } = useI18n();

  const handleExport = () => {
    const headers = [t('table.rank'), t('table.ticker'), t('table.name'), t('table.sector'), t('table.score'), t('table.earningsVisibility'), t('table.valuationMargin'), t('table.catalystTimeline'), t('table.downsideControl'), t('table.rating')];
    const rows = data.map((s) => [
      s.rank,
      s.ticker,
      s.name || '',
      s.sector || '',
      s.composite_score?.toFixed(4) ?? '',
      s.earnings_visibility?.toFixed(4) ?? '',
      s.valuation_margin?.toFixed(4) ?? '',
      s.catalyst_timeline?.toFixed(4) ?? '',
      s.downside_control?.toFixed(4) ?? '',
      s.tier_label,
    ]);

    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `athene-rankings-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button
      onClick={handleExport}
      className="tech-ctrl rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-700 active:bg-gray-800 sm:px-3 sm:py-1.5 dark:border dark:border-cyan-500/30 dark:bg-cyan-500/15 dark:text-cyan-300 dark:hover:bg-cyan-500/25"
    >
      {t('screener.exportCsv')}
    </button>
  );
}
