import { useMeta } from '../../hooks/useMeta';

export function Footer() {
  const { data: meta } = useMeta();

  return (
    <footer className="border-t border-gray-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-4 text-center text-xs text-gray-500">
        <p>
          Athene Stock Screener &middot; Data from Yahoo Finance
          {meta && <> &middot; Last updated: {meta.date} &middot; {meta.ticker_count} stocks</>}
        </p>
        <p className="mt-1">For educational purposes only. Not financial advice.</p>
      </div>
    </footer>
  );
}
