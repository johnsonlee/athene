import type { FilterState, TierKey } from '../../types';
import { useI18n } from '../../lib/i18n';

const TIER_KEYS: TierKey[] = ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell'];

interface Props {
  filter: FilterState;
  onChange: (f: FilterState) => void;
  sectors: string[];
}

export function FilterPanel({ filter, onChange, sectors }: Props) {
  const { t } = useI18n();

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg bg-white p-3 shadow-sm dark:bg-gray-800">
      {/* Search */}
      <input
        type="text"
        placeholder={t('screener.searchPlaceholder')}
        value={filter.search}
        onChange={(e) => onChange({ ...filter, search: e.target.value })}
        className="rounded border px-3 py-1.5 text-sm outline-none focus:border-blue-500 dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600"
      />

      {/* Sector filter */}
      <select
        value={filter.sectors[0] || ''}
        onChange={(e) =>
          onChange({ ...filter, sectors: e.target.value ? [e.target.value] : [] })
        }
        className="rounded border px-2 py-1.5 text-sm dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600"
      >
        <option value="">{t('screener.allSectors')}</option>
        {sectors.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      {/* Tier filter */}
      <div className="flex gap-1">
        {TIER_KEYS.map((key) => {
          const active = filter.tiers.includes(key);
          return (
            <button
              key={key}
              onClick={() => {
                const tiers = active
                  ? filter.tiers.filter((t) => t !== key)
                  : [...filter.tiers, key];
                onChange({ ...filter, tiers });
              }}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                active
                  ? 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600'
              }`}
            >
              {t(`tier.${key}` as any)}
            </button>
          );
        })}
      </div>

      {/* Reset */}
      <button
        onClick={() =>
          onChange({ search: '', sectors: [], tiers: [], minScore: -Infinity, maxScore: Infinity })
        }
        className="text-xs text-blue-600 hover:underline"
      >
        {t('screener.reset')}
      </button>
    </div>
  );
}
