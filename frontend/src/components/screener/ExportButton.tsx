import type { RankedStock } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  data: RankedStock[];
}

export function ExportButton({ data }: Props) {
  const { t } = useI18n();

  const handleExport = () => {
    const headers = [t('table.rank'), t('table.ticker'), t('table.name'), t('table.sector'), t('table.alphaScore'), 'VM', 'EV', 'Timing'];
    const rows = data.map((s) => [
      s.rank,
      s.ticker,
      s.name || '',
      s.sector || '',
      s.alpha_score?.toFixed(2) ?? '',
      s.alpha_vm?.toFixed(2) ?? '',
      s.alpha_ev?.toFixed(2) ?? '',
      s.alpha_timing?.toFixed(2) ?? '',
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
