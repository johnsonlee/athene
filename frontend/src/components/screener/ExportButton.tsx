import type { RankedStock } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  data: RankedStock[];
}

export function ExportButton({ data }: Props) {
  const { t } = useI18n();

  const handleExport = () => {
    const headers = [t('table.rank'), t('table.ticker'), t('table.name'), t('table.sector'), t('table.score'), t('table.fundamental'), t('table.technical'), t('table.sentiment'), t('table.rating')];
    const rows = data.map((s) => [
      s.rank,
      s.ticker,
      s.name || '',
      s.sector || '',
      s.composite_score?.toFixed(4) ?? '',
      s.fundamental_score?.toFixed(4) ?? '',
      s.technical_score?.toFixed(4) ?? '',
      s.sentiment_score?.toFixed(4) ?? '',
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
      className="rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-gray-300"
    >
      {t('screener.exportCsv')}
    </button>
  );
}
