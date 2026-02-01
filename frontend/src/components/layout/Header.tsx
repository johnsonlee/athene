import { Link, useLocation } from 'react-router-dom';
import { useI18n } from '../../lib/i18n';

export function Header() {
  const location = useLocation();
  const { t, locale, setLocale } = useI18n();

  const NAV_ITEMS = [
    { path: '/', label: t('nav.dashboard') },
    { path: '/screener', label: t('nav.screener') },
    { path: '/about', label: t('nav.about') },
  ];

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-xl font-bold text-gray-900">
          <img src={import.meta.env.BASE_URL + 'logo.svg'} alt="Athene" className="h-8 w-8" />
          Athene
        </Link>
        <div className="flex items-center gap-3">
          <nav className="flex gap-1">
            {NAV_ITEMS.map(({ path, label }) => {
              const active = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    active
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
          <button
            onClick={() => setLocale(locale === 'en' ? 'zh' : 'en')}
            className="rounded-md border px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100"
          >
            {locale === 'en' ? '中文' : 'EN'}
          </button>
        </div>
      </div>
    </header>
  );
}
