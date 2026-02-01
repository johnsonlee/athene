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

export function ScreenerTable({ data }: Props) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'rank', desc: false }]);
  const { t } = useI18n();

  const columns = useMemo<ColumnDef<RankedStock, any>[]>(
    () => [
      {
        accessorKey: 'rank',
        header: t('table.rank'),
        size: 50,
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-300">{getValue() as number}</span>
        ),
      },
      {
        accessorKey: 'ticker',
        header: t('table.ticker'),
        cell: ({ row }) => (
          <Link
            to={`/stock/${row.original.ticker}`}
            className="font-mono font-semibold text-blue-600 hover:underline dark:text-blue-400"
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
        accessorKey: 'sector',
        header: t('table.sector'),
        size: 140,
        cell: ({ getValue }) => (
          <span className="text-xs text-gray-600 dark:text-gray-400">{getValue() as string}</span>
        ),
      },
      {
        accessorKey: 'composite_score',
        header: t('table.score'),
        cell: ({ getValue }) => (
          <span className="font-mono font-medium text-gray-900 dark:text-white">{formatScore(getValue() as number)}</span>
        ),
      },
      {
        accessorKey: 'fundamental_score',
        header: t('table.fundamental'),
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-300">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'technical_score',
        header: t('table.technical'),
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-300">{formatScore(getValue() as number | null)}</span>
        ),
      },
      {
        accessorKey: 'sentiment_score',
        header: t('table.sentiment'),
        cell: ({ getValue }) => (
          <span className="font-mono text-sm text-gray-700 dark:text-gray-300">{formatScore(getValue() as number | null)}</span>
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
    [t]
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

  return (
    <div className="overflow-x-auto rounded-lg bg-white shadow-sm dark:bg-gray-800">
      <table className="w-full text-left text-sm">
        <thead className="border-b bg-gray-50 dark:bg-gray-900 dark:border-gray-700">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((header) => (
                <th
                  key={header.id}
                  className="cursor-pointer px-3 py-2 text-xs font-semibold text-gray-600 select-none dark:text-gray-400"
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
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-b last:border-0 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Pagination */}
      <div className="flex items-center justify-between border-t px-3 py-2 text-sm text-gray-600 dark:border-gray-700 dark:text-gray-400">
        <span>
          {t('screener.page', {
            current: table.getState().pagination.pageIndex + 1,
            total: table.getPageCount(),
          })}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded border px-3 py-1 hover:bg-gray-100 disabled:opacity-40 dark:border-gray-600 dark:hover:bg-gray-700"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            {t('screener.prev')}
          </button>
          <button
            className="rounded border px-3 py-1 hover:bg-gray-100 disabled:opacity-40 dark:border-gray-600 dark:hover:bg-gray-700"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            {t('screener.next')}
          </button>
        </div>
      </div>
    </div>
  );
}
