import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  type SortingState,
  type PaginationState,
  type ColumnDef,
} from '@tanstack/react-table';
import type { RankedStock } from '../../types';
import { formatPercent, formatScore } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

interface Props {
  data: RankedStock[];
}

type Translate = ReturnType<typeof useI18n>['t'];
type IndustryTranslate = ReturnType<typeof useI18n>['tIndustry'];
type ColumnFilter = {
  text: string;
  min: string;
  max: string;
};
type ColumnFiltersState = Record<string, ColumnFilter>;
type SortDirection = 'asc' | 'desc';
type ColumnMenuState = {
  columnId: string;
  left: number;
  top: number;
};

const EMPTY_COLUMN_FILTER: ColumnFilter = {
  text: '',
  min: '',
  max: '',
};
const COLUMN_MENU_WIDTH = 224;
const COLUMN_MENU_VIEWPORT_MARGIN = 8;

function translateSector(t: Translate, sector: string): string {
  return t(`sector.${sector}` as Parameters<Translate>[0]) || sector;
}

function getMa200Deviation(stock: RankedStock): number | undefined {
  if (stock.close == null || stock.sma_200 == null || stock.sma_200 === 0) return undefined;
  return (stock.close - stock.sma_200) / stock.sma_200;
}

function getMa200DeviationOrNeutral(stock: RankedStock): number {
  return getMa200Deviation(stock) ?? 0;
}

function getBaseScore(stock: RankedStock): number | undefined {
  if (stock.alpha_vm == null || stock.alpha_ev == null) return undefined;
  return (stock.alpha_vm * stock.alpha_ev) / 100;
}

function getFiveDayReferenceMa200Deviation(stock: RankedStock): number | undefined {
  if (
    stock.ma200_ref_5d_close == null
    || stock.ma200_ref_5d_sma_200 == null
    || stock.ma200_ref_5d_sma_200 === 0
  ) {
    return undefined;
  }
  return (stock.ma200_ref_5d_close - stock.ma200_ref_5d_sma_200) / stock.ma200_ref_5d_sma_200;
}

function getMa200DistanceDelta5d(stock: RankedStock): number | undefined {
  const current = getMa200Deviation(stock);
  const reference = getFiveDayReferenceMa200Deviation(stock);
  if (current == null || reference == null) return undefined;
  return Math.abs(current) - Math.abs(reference);
}

function getMa200DistanceDelta5dOrNeutral(stock: RankedStock): number {
  return getMa200DistanceDelta5d(stock) ?? 0;
}

function normalizeDisplayPercent(value: number): number {
  return Math.abs(value) < 0.0005 ? 0 : value;
}

function formatSignedPercent(value: number | undefined): string {
  if (value == null) return formatPercent(value);
  const normalized = normalizeDisplayPercent(value);
  if (normalized === 0) return '-';
  return normalized > 0 ? `+${formatPercent(normalized)}` : formatPercent(normalized);
}

function wideOnlyColumnClass(columnId: string): string {
  return columnId === 'ma200Deviation' || columnId === 'ma200DistanceDelta5d' ? 'hidden xl:table-cell' : '';
}

function FunnelIcon({ active }: { active: boolean }) {
  return (
    <svg
      aria-hidden="true"
      className={active ? 'text-blue-600 dark:text-cyan-300' : 'text-gray-500 dark:text-gray-500'}
      height="14"
      viewBox="0 0 16 16"
      width="14"
    >
      <path
        d="M2.5 4.5h11L9.2 9.1v3.1l-2.4 1.2V9.1L2.5 4.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

const NUMERIC_FILTER_COLUMN_IDS = new Set([
  'rank',
  'alpha_score',
  'baseScore',
  'alpha_vm',
  'alpha_ev',
  'alpha_timing',
  'ma200Deviation',
  'ma200DistanceDelta5d',
]);

const TEXT_FILTER_COLUMN_IDS = new Set([
  'ticker',
  'name',
  'industry',
]);

function getNumericColumnValue(stock: RankedStock, columnId: string): number | undefined {
  switch (columnId) {
    case 'rank':
      return stock.rank;
    case 'baseScore':
      return getBaseScore(stock);
    case 'alpha_score':
      return stock.alpha_score ?? stock.composite_score;
    case 'alpha_vm':
      return stock.alpha_vm ?? undefined;
    case 'alpha_ev':
      return stock.alpha_ev ?? undefined;
    case 'alpha_timing':
      return stock.alpha_timing ?? undefined;
    case 'ma200Deviation':
      return getMa200DeviationOrNeutral(stock);
    case 'ma200DistanceDelta5d':
      return getMa200DistanceDelta5dOrNeutral(stock);
    default:
      return undefined;
  }
}

function getTextColumnValue(stock: RankedStock, columnId: string, t: Translate, tIndustry: IndustryTranslate): string {
  switch (columnId) {
    case 'ticker':
      return stock.ticker;
    case 'name':
      return stock.name ?? '';
    case 'industry': {
      const rawText = [stock.sector, stock.industry].filter(Boolean).join(' / ');
      const displayText = [
        stock.sector ? translateSector(t, stock.sector) : '',
        stock.industry ? tIndustry(stock.industry) : '',
      ].filter(Boolean).join(' / ');
      return `${rawText} ${displayText}`;
    }
    default:
      return '';
  }
}

function isNumericFilterColumn(columnId: string): boolean {
  return NUMERIC_FILTER_COLUMN_IDS.has(columnId);
}

function isTextFilterColumn(columnId: string): boolean {
  return TEXT_FILTER_COLUMN_IDS.has(columnId);
}

function isPercentFilterColumn(columnId: string): boolean {
  return columnId === 'ma200Deviation' || columnId === 'ma200DistanceDelta5d';
}

function parseFilterNumber(value: string, isPercent: boolean): number | undefined {
  if (value.trim() === '') return undefined;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return undefined;
  return isPercent ? parsed / 100 : parsed;
}

function filterRankedStocks(
  data: RankedStock[],
  filters: ColumnFiltersState,
  t: Translate,
  tIndustry: IndustryTranslate
): RankedStock[] {
  const activeFilters = Object.entries(filters).filter(([, filter]) => (
    filter.text.trim() !== '' || filter.min.trim() !== '' || filter.max.trim() !== ''
  ));
  if (activeFilters.length === 0) return data;

  return data.filter((stock) => activeFilters.every(([columnId, filter]) => {
    if (isNumericFilterColumn(columnId)) {
      const value = getNumericColumnValue(stock, columnId);
      if (value == null) return false;
      const min = parseFilterNumber(filter.min, isPercentFilterColumn(columnId));
      const max = parseFilterNumber(filter.max, isPercentFilterColumn(columnId));
      if (min != null && value < min) return false;
      if (max != null && value > max) return false;
      return true;
    }

    const text = filter.text.trim().toLowerCase();
    if (!text) return true;
    return getTextColumnValue(stock, columnId, t, tIndustry).toLowerCase().includes(text);
  }));
}

/* ── Mobile card for a single stock ── */
function StockCard({ stock, t, tIndustry }: { stock: RankedStock; t: ReturnType<typeof useI18n>['t']; tIndustry: ReturnType<typeof useI18n>['tIndustry'] }) {
  return (
    <Link
      to={`/stock/${stock.ticker}`}
      className="tech-card block p-3 transition-all active:scale-[0.99]"
    >
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-gray-400 dark:text-gray-600">#{stock.rank}</span>
            <span className="font-mono text-sm font-bold text-blue-600 dark:text-cyan-400">{stock.ticker}</span>
          </div>
          <p className="mt-0.5 truncate text-xs text-gray-500 dark:text-gray-500">{stock.name}</p>
        </div>
        <div className="ml-3 text-right">
          <p className="font-mono text-base font-bold text-gray-900 dark:text-white">{formatScore(stock.alpha_score ?? stock.composite_score)}</p>
          {(stock.industry || stock.sector) && (
            <p className="text-[10px] text-gray-400 dark:text-gray-600">
              {stock.sector ? translateSector(t, stock.sector) : ''}
              {stock.sector && stock.industry ? ' · ' : ''}
              {stock.industry ? tIndustry(stock.industry) : ''}
            </p>
          )}
        </div>
      </div>
      {/* Mini score bars */}
      <div className="mt-2 grid grid-cols-3 gap-2 text-[10px]">
        <div>
          <span className="text-gray-400 dark:text-gray-600">VM</span>
          <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(stock.alpha_vm)}</p>
        </div>
        <div>
          <span className="text-gray-400 dark:text-gray-600">EV</span>
          <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(stock.alpha_ev)}</p>
        </div>
        <div>
          <span className="text-gray-400 dark:text-gray-600">Timing</span>
          <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(stock.alpha_timing)}</p>
        </div>
      </div>
    </Link>
  );
}

export function ScreenerTable({ data }: Props) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 50 });
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>({});
  const [openColumnMenu, setOpenColumnMenu] = useState<ColumnMenuState | null>(null);
  const tableMenuBoundaryRef = useRef<HTMLDivElement | null>(null);
  const columnMenuRef = useRef<HTMLDivElement | null>(null);
  const { t, tIndustry } = useI18n();
  const filteredTableData = useMemo(
    () => filterRankedStocks(data, columnFilters, t, tIndustry),
    [data, columnFilters, t, tIndustry]
  );

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target;
      if (target instanceof Node && tableMenuBoundaryRef.current?.contains(target)) return;
      if (target instanceof Node && columnMenuRef.current?.contains(target)) return;
      setOpenColumnMenu(null);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpenColumnMenu(null);
    };

    const closeColumnMenu = () => setOpenColumnMenu(null);

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', closeColumnMenu);
    window.addEventListener('scroll', closeColumnMenu, true);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', closeColumnMenu);
      window.removeEventListener('scroll', closeColumnMenu, true);
    };
  }, [openColumnMenu]);

  const toggleColumnMenu = (columnId: string, button: HTMLButtonElement) => {
    setOpenColumnMenu((current) => {
      if (current?.columnId === columnId) return null;

      const rect = button.getBoundingClientRect();
      const maxLeft = window.innerWidth - COLUMN_MENU_WIDTH - COLUMN_MENU_VIEWPORT_MARGIN;
      const left = Math.max(
        COLUMN_MENU_VIEWPORT_MARGIN,
        Math.min(rect.right - COLUMN_MENU_WIDTH, maxLeft)
      );

      return {
        columnId,
        left,
        top: rect.bottom + 4,
      };
    });
  };

  const setColumnSort = (columnId: string, direction: SortDirection) => {
    const desc = direction === 'desc';
    setPagination((current) => ({ ...current, pageIndex: 0 }));
    setSorting((current) => {
      const existingIndex = current.findIndex((sort) => sort.id === columnId);
      if (existingIndex === -1) {
        return [...current, { id: columnId, desc }];
      }
      return current.map((sort, index) => (
        index === existingIndex ? { ...sort, desc } : sort
      ));
    });
  };

  const clearColumnSort = (columnId: string) => {
    setPagination((current) => ({ ...current, pageIndex: 0 }));
    setSorting((current) => current.filter((sort) => sort.id !== columnId));
  };

  const updateColumnFilter = (columnId: string, patch: Partial<ColumnFilter>) => {
    setPagination((current) => ({ ...current, pageIndex: 0 }));
    setColumnFilters((current) => {
      const nextFilter = { ...EMPTY_COLUMN_FILTER, ...current[columnId], ...patch };
      const next = { ...current };
      if (nextFilter.text.trim() === '' && nextFilter.min.trim() === '' && nextFilter.max.trim() === '') {
        delete next[columnId];
      } else {
        next[columnId] = nextFilter;
      }
      return next;
    });
  };

  const clearColumnFilter = (columnId: string) => {
    setPagination((current) => ({ ...current, pageIndex: 0 }));
    setColumnFilters((current) => {
      const next = { ...current };
      delete next[columnId];
      return next;
    });
  };

  const renderColumnFilterControls = (columnId: string) => {
    const filter = columnFilters[columnId] ?? EMPTY_COLUMN_FILTER;
    const inputClass = "tech-ctrl h-8 w-full rounded border border-gray-200 bg-white px-2 text-xs font-normal normal-case tracking-normal text-gray-700 placeholder:text-gray-400 focus:border-blue-400 focus:outline-none dark:border-slate-700 dark:bg-slate-950 dark:text-gray-200 dark:placeholder:text-gray-600 dark:focus:border-cyan-500";

    if (isNumericFilterColumn(columnId)) {
      const suffix = isPercentFilterColumn(columnId) ? '%' : '';
      return (
        <>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-500">
            {t('filter.range')}
          </p>
          <div className="grid grid-cols-2 gap-2">
            <label className="space-y-1">
              <span className="block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-500">
                {t('filter.min')}{suffix}
              </span>
              <input
                aria-label={`${t('filter.min')}${suffix}`}
                className={inputClass}
                inputMode="decimal"
                value={filter.min}
                onChange={(event) => updateColumnFilter(columnId, { min: event.target.value })}
              />
            </label>
            <label className="space-y-1">
              <span className="block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-500">
                {t('filter.max')}{suffix}
              </span>
              <input
                aria-label={`${t('filter.max')}${suffix}`}
                className={inputClass}
                inputMode="decimal"
                value={filter.max}
                onChange={(event) => updateColumnFilter(columnId, { max: event.target.value })}
              />
            </label>
          </div>
        </>
      );
    }

    if (isTextFilterColumn(columnId)) {
      return (
        <label className="block space-y-1">
          <span className="block text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-500">
            {t('filter.search')}
          </span>
          <input
            aria-label={t('filter.search')}
            className={inputClass}
            placeholder={t('filter.search')}
            value={filter.text}
            onChange={(event) => updateColumnFilter(columnId, { text: event.target.value })}
          />
        </label>
      );
    }

    return null;
  };

  const renderColumnMenu = (state: ColumnMenuState) => {
    const columnId = state.columnId;
    const filter = columnFilters[columnId] ?? EMPTY_COLUMN_FILTER;
    const sortIndex = sorting.findIndex((sort) => sort.id === columnId);
    const sort = sortIndex === -1 ? undefined : sorting[sortIndex];
    const filterActive = filter.text.trim() !== '' || filter.min.trim() !== '' || filter.max.trim() !== '';
    const sortButtonClass = (active: boolean) => (
      `flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs font-medium normal-case tracking-normal transition-colors ${
        active
          ? 'bg-blue-50 text-blue-700 dark:bg-cyan-500/10 dark:text-cyan-300'
          : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-cyan-500/10'
      }`
    );

    return (
      <div
        ref={columnMenuRef}
        className="fixed z-50 w-56 rounded-md border border-gray-200 bg-white p-1.5 text-left shadow-lg dark:border-cyan-500/20 dark:bg-slate-950"
        style={{ left: state.left, top: state.top }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="space-y-0.5">
          <button
            className={sortButtonClass(sort?.desc === false)}
            type="button"
            onClick={() => setColumnSort(columnId, 'asc')}
          >
            <span className="w-4 text-center font-mono">↑</span>
            {t('filter.sortAsc')}
          </button>
          <button
            className={sortButtonClass(sort?.desc === true)}
            type="button"
            onClick={() => setColumnSort(columnId, 'desc')}
          >
            <span className="w-4 text-center font-mono">↓</span>
            {t('filter.sortDesc')}
          </button>
          {sort && (
            <button
              className={sortButtonClass(false)}
              type="button"
              onClick={() => clearColumnSort(columnId)}
            >
              <span className="w-4 text-center font-mono">×</span>
              {t('filter.clearSort')}
            </button>
          )}
        </div>
        <div className="mt-1.5 border-t border-gray-100 pt-2 dark:border-slate-800">
          {renderColumnFilterControls(columnId)}
          {filterActive && (
            <button
              className="mt-2 w-full rounded px-2 py-1.5 text-left text-xs font-medium normal-case tracking-normal text-gray-600 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-cyan-500/10"
              type="button"
              onClick={() => clearColumnFilter(columnId)}
            >
              {t('filter.clearFilter')}
            </button>
          )}
        </div>
      </div>
    );
  };

  const columns = useMemo<ColumnDef<RankedStock>[]>(
    () => [
      {
        accessorKey: 'rank',
        header: t('table.rank'),
        size: 50,
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{getValue() as number}</span>
        ),
      },
      {
        accessorKey: 'ticker',
        header: t('table.ticker'),
        cell: ({ row }) => (
          <Link
            to={`/stock/${row.original.ticker}`}
            className="font-mono font-semibold text-blue-600 hover:underline dark:text-cyan-400"
          >
            {row.original.ticker}
          </Link>
        ),
      },
      {
        accessorKey: 'name',
        header: t('table.name'),
        size: 200,
        cell: ({ getValue }) => (
          <span className="truncate text-sm text-gray-700 dark:text-gray-300">{getValue() as string}</span>
        ),
      },
      {
        accessorKey: 'industry',
        header: t('table.sectorIndustry'),
        size: 220,
        cell: ({ row }) => {
          const industry = row.original.industry;
          const sector = row.original.sector;
          const sectorLabel = sector ? translateSector(t, sector) : '';
          const industryLabel = industry ? tIndustry(industry) : '';
          return (
            <span className="text-xs text-gray-600 dark:text-gray-500">
              {sectorLabel && industryLabel
                ? <>{sectorLabel}<span className="mx-1 text-gray-300 dark:text-gray-700">&middot;</span>{industryLabel}</>
                : sectorLabel || industryLabel || '\u2014'}
            </span>
          );
        },
      },
      {
        accessorKey: 'alpha_score',
        header: t('table.alphaScore'),
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        id: 'baseScore',
        accessorFn: getBaseScore,
        header: t('table.baseScore'),
        sortUndefined: 'last',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'alpha_vm',
        header: 'VM',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'alpha_ev',
        header: 'EV',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'alpha_timing',
        header: 'Timing',
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        id: 'ma200Deviation',
        accessorFn: getMa200DeviationOrNeutral,
        header: t('table.ma200Deviation'),
        sortUndefined: 'last',
        cell: ({ getValue }) => {
          const value = normalizeDisplayPercent(getValue() as number);
          const colorClass = value === 0
              ? 'text-gray-500 dark:text-gray-500'
              : value > 0
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-red-600 dark:text-red-400';
          return (
            <span className={`font-mono text-sm ${colorClass}`}>{value === 0 ? '-' : formatPercent(value)}</span>
          );
        },
      },
      {
        id: 'ma200DistanceDelta5d',
        accessorFn: getMa200DistanceDelta5dOrNeutral,
        header: t('table.ma200DistanceDelta5d'),
        sortUndefined: 'last',
        cell: ({ getValue }) => {
          const value = normalizeDisplayPercent(getValue() as number);
          const colorClass = value > 0
              ? 'text-amber-600 dark:text-amber-400'
              : value < 0
                ? 'text-sky-600 dark:text-sky-400'
                : 'text-gray-600 dark:text-gray-400';
          return (
            <span className={`font-mono text-sm ${colorClass}`}>{formatSignedPercent(value)}</span>
          );
        },
      },
    ],
    [t, tIndustry]
  );

  const table = useReactTable({
    data: filteredTableData,
    columns,
    state: { sorting, pagination },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  const paginatedRows = table.getRowModel().rows;
  const sortedData = paginatedRows.map((r) => r.original);

  return (
    <>
      {/* ── Mobile: card list ── */}
      <div className="space-y-2 md:hidden">
        {sortedData.map((stock) => (
          <StockCard key={stock.ticker} stock={stock} t={t} tIndustry={tIndustry} />
        ))}
      </div>

      {/* ── Desktop: table ── */}
      <div ref={tableMenuBoundaryRef} className="tech-card hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 dark:border-cyan-500/10 dark:bg-slate-900/50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => {
                  const columnId = header.column.id;
                  const filter = columnFilters[columnId] ?? EMPTY_COLUMN_FILTER;
                  const filterActive = filter.text.trim() !== '' || filter.min.trim() !== '' || filter.max.trim() !== '';
                  const sortIndex = sorting.findIndex((sort) => sort.id === columnId);
                  const sort = sortIndex === -1 ? undefined : sorting[sortIndex];
                  const menuOpen = openColumnMenu?.columnId === columnId;

                  return (
                    <th
                      key={header.id}
                      className={`${wideOnlyColumnClass(columnId)} relative px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-600 select-none dark:text-gray-500`}
                    >
                      <div className="flex min-w-0 items-center justify-between gap-1">
                        <div className="flex min-w-0 items-center gap-1">
                          <span className="truncate">
                            {flexRender(header.column.columnDef.header, header.getContext())}
                          </span>
                          {sort && (
                            <span className="inline-flex shrink-0 items-center gap-0.5 text-blue-500 dark:text-cyan-400">
                              <span>{sort.desc ? '↓' : '↑'}</span>
                              <span>{sortIndex + 1}</span>
                            </span>
                          )}
                        </div>
                        <button
                          aria-label={t('filter.open')}
                          className={`inline-flex h-6 w-6 shrink-0 items-center justify-center rounded border transition-colors ${
                            menuOpen || filterActive
                              ? 'border-blue-200 bg-blue-50 text-blue-600 dark:border-cyan-500/30 dark:bg-cyan-500/10 dark:text-cyan-300'
                              : 'border-transparent text-gray-500 hover:border-gray-200 hover:bg-white dark:text-gray-500 dark:hover:border-cyan-500/20 dark:hover:bg-cyan-500/10'
                          }`}
                          title={t('filter.open')}
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            toggleColumnMenu(columnId, event.currentTarget);
                          }}
                        >
                          <FunnelIcon active={menuOpen || filterActive} />
                        </button>
                      </div>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {paginatedRows.map((row) => (
              <tr key={row.id} className="tech-row border-b border-gray-100 last:border-0 transition-colors hover:bg-gray-50 dark:border-slate-700/50 dark:hover:bg-transparent">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className={`${wideOnlyColumnClass(cell.column.id)} px-3 py-2`}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {openColumnMenu && renderColumnMenu(openColumnMenu)}

      {/* Pagination */}
      <div className="tech-card mt-2 flex items-center justify-between px-3 py-2.5 text-sm text-gray-600 dark:text-gray-400">
        <span className="font-mono text-xs">
          {t('screener.page', {
            current: table.getState().pagination.pageIndex + 1,
            total: table.getPageCount(),
          })}
        </span>
        <div className="flex gap-2">
          <button
            className="tech-ctrl rounded border border-gray-200 px-4 py-2 text-sm transition-colors hover:bg-gray-100 disabled:opacity-40 dark:border-gray-600 dark:hover:bg-gray-700"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            {t('screener.prev')}
          </button>
          <button
            className="tech-ctrl rounded border border-gray-200 px-4 py-2 text-sm transition-colors hover:bg-gray-100 disabled:opacity-40 dark:border-gray-600 dark:hover:bg-gray-700"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            {t('screener.next')}
          </button>
        </div>
      </div>
    </>
  );
}
