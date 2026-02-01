import type { FilterState, TierKey } from '../../types';

const TIERS: { key: TierKey; label: string }[] = [
  { key: 'strong_buy', label: 'Strong Buy' },
  { key: 'buy', label: 'Buy' },
  { key: 'hold', label: 'Hold' },
  { key: 'sell', label: 'Sell' },
  { key: 'strong_sell', label: 'Strong Sell' },
];

interface Props {
  filter: FilterState;
  onChange: (f: FilterState) => void;
  sectors: string[];
}

export function FilterPanel({ filter, onChange, sectors }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg bg-white p-3 shadow-sm">
      {/* Search */}
      <input
        type="text"
        placeholder="Search ticker or name..."
        value={filter.search}
        onChange={(e) => onChange({ ...filter, search: e.target.value })}
        className="rounded border px-3 py-1.5 text-sm outline-none focus:border-blue-500"
      />

      {/* Sector filter */}
      <select
        value={filter.sectors[0] || ''}
        onChange={(e) =>
          onChange({ ...filter, sectors: e.target.value ? [e.target.value] : [] })
        }
        className="rounded border px-2 py-1.5 text-sm"
      >
        <option value="">All Sectors</option>
        {sectors.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      {/* Tier filter */}
      <div className="flex gap-1">
        {TIERS.map(({ key, label }) => {
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
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {label}
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
        Reset
      </button>
    </div>
  );
}
