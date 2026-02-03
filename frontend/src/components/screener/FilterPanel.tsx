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
    <div className="tech-card space-y-3 p-3 md:flex md:flex-wrap md:items-center md:gap-3 md:space-y-0">
      {/* Search + Sector row */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder={t('screener.searchPlaceholder')}
          value={filter.search}
          onChange={(e) => onChange({ ...filter, search: e.target.value })}
          className="tech-input min-w-0 flex-1 rounded border border-gray-200 bg-white px-3 py-2 text-sm outline-none transition-colors focus:border-blue-500 md:py-1.5 dark:border-slate-600/50 dark:bg-slate-800/50 dark:text-gray-200"
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
      </div>

      {/* Tier filter + Reset */}
      <div className="flex items-center gap-2">
        <div className="flex flex-wrap gap-1">
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
                className={`rounded px-2.5 py-1.5 text-xs font-medium transition-colors ${
                  active
                    ? 'tech-btn-active bg-gray-900 text-white dark:bg-transparent'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-slate-700/50 dark:text-gray-400 dark:hover:bg-slate-600/50'
                }`}
              >
                {t(`tier.${key}` as any)}
              </button>
            );
          })}
        </div>
        <button
          onClick={() =>
            onChange({ search: '', sectors: [], tiers: [], minScore: -Infinity, maxScore: Infinity })
          }
          className="shrink-0 text-xs text-blue-600 hover:underline dark:text-cyan-400"
        >
          {t('screener.reset')}
        </button>
      </div>
    </div>
  );
}
