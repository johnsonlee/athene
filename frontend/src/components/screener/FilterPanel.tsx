import type { FilterState } from '../../types';
import { useI18n } from '../../lib/i18n';

interface Props {
  filter: FilterState;
  onChange: (f: FilterState) => void;
  sectors: string[];
}

export function FilterPanel({ filter, onChange, sectors }: Props) {
  const { t } = useI18n();

  return (
    <div className="tech-card flex items-center gap-3 p-3">
      <input
        type="text"
        value={filter.search}
        onChange={(e) => onChange({ ...filter, search: e.target.value })}
        placeholder={t('screener.searchPlaceholder')}
        className="rounded border border-gray-200 px-2 py-2 text-sm md:py-1.5 dark:border-slate-600/50 dark:bg-slate-800/50 dark:text-gray-200"
      />
      <select
        value={filter.sectors[0] || ''}
        onChange={(e) =>
          onChange({ ...filter, sectors: e.target.value ? [e.target.value] : [] })
        }
        className="rounded border border-gray-200 px-2 py-2 text-sm md:py-1.5 dark:border-slate-600/50 dark:bg-slate-800/50 dark:text-gray-200"
      >
        <option value="">{t('screener.allSectors')}</option>
        {sectors.map((s) => (
          <option key={s} value={s}>{t(`sector.${s}` as any) || s}</option>
        ))}
      </select>
      <button
        onClick={() =>
          onChange({ search: '', sectors: [], minScore: -Infinity, maxScore: Infinity })
        }
        className="shrink-0 text-xs text-blue-600 hover:underline dark:text-cyan-400"
      >
        {t('screener.reset')}
      </button>
    </div>
  );
}
