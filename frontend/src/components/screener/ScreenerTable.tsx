import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  type SortingState,
  type ColumnDef,
} from '@tanstack/react-table';
import type { RankedStock } from '../../types';
import { ScoreBadge } from '../common/ScoreBadge';
import { formatScore } from '../../lib/formatters';
import { useI18n } from '../../lib/i18n';

interface Props {
  data: RankedStock[];
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
            <ScoreBadge tier={stock.tier} label={t(`tier.${stock.tier}` as any)} />
          </div>
          <p className="mt-0.5 truncate text-xs text-gray-500 dark:text-gray-500">{stock.name}</p>
        </div>
        <div className="ml-3 text-right">
          <p className="font-mono text-base font-bold text-gray-900 dark:text-white">{formatScore(stock.composite_score)}</p>
          {(stock.industry || stock.sector) && (
            <p className="text-[10px] text-gray-400 dark:text-gray-600">
              {stock.sector ? (t(`sector.${stock.sector}` as any) || stock.sector) : ''}
              {stock.sector && stock.industry ? ' · ' : ''}
              {stock.industry ? tIndustry(stock.industry) : ''}
            </p>
          )}
        </div>
      </div>
      {/* Mini score bars */}
      <div className="mt-2 grid grid-cols-4 gap-2 text-[10px]">
        <div>
          <span className="text-gray-400 dark:text-gray-600">{t('table.earningsVisibility')}</span>
          <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(stock.earnings_visibility)}</p>
        </div>
        <div>
          <span className="text-gray-400 dark:text-gray-600">{t('table.valuationMargin')}</span>
          <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(stock.valuation_margin)}</p>
        </div>
        <div>
          <span className="text-gray-400 dark:text-gray-600">{t('table.catalystTimeline')}</span>
          <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(stock.catalyst_timeline)}</p>
        </div>
        <div>
          <span className="text-gray-400 dark:text-gray-600">{t('table.downsideControl')}</span>
          <p className="font-mono font-medium text-gray-700 dark:text-gray-300">{formatScore(stock.downside_control)}</p>
        </div>
      </div>
    </Link>
  );
}

export function ScreenerTable({ data }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'rank', desc: false }]);
  const { t, tIndustry } = useI18n();

  const columns = useMemo<ColumnDef<RankedStock, any>[]>(
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
          const sectorLabel = sector ? (t(`sector.${sector}` as any) || sector) : '';
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
        accessorKey: 'composite_score',
        header: t('table.score'),
        cell: ({ getValue }) => (
          <span className="font-mono font-medium text-gray-900 dark:text-white">{formatScore(getValue() as number)}</span>
        ),
      },
      {
        accessorKey: 'earnings_visibility',
        header: t('table.earningsVisibility'),
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'valuation_margin',
        header: t('table.valuationMargin'),
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'catalyst_timeline',
        header: t('table.catalystTimeline'),
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'downside_control',
        header: t('table.downsideControl'),
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-400">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'tier_label',
        header: t('table.rating'),
        cell: ({ row }) => (
          <ScoreBadge tier={row.original.tier} label={t(`tier.${row.original.tier}` as any)} />
        ),
      },
    ],
    [t, tIndustry]
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 50 } },
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
      <div className="tech-card hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 dark:border-cyan-500/10 dark:bg-slate-900/50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="cursor-pointer px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-600 select-none dark:text-gray-500"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{ asc: ' \u2191', desc: ' \u2193' }[header.column.getIsSorted() as string] ?? ''}
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {paginatedRows.map((row) => (
              <tr key={row.id} className="tech-row border-b border-gray-100 last:border-0 transition-colors hover:bg-gray-50 dark:border-slate-700/50 dark:hover:bg-transparent">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="tech-card flex items-center justify-between px-3 py-2.5 text-sm text-gray-600 md:mt-0 dark:text-gray-500">
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
