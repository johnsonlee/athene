import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useI18n } from '../../lib/i18n';
import { useTheme } from '../../lib/theme';

export function Header() {
  const location = useLocation();
  const { t, locale, setLocale } = useI18n();
  const { theme, toggle } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  const NAV_ITEMS = [
    { path: '/', label: t('nav.dashboard') },
    { path: '/screener', label: t('nav.screener') },
    { path: '/about', label: t('nav.about') },
  ];

  return (
    <header className="tech-bar tech-glow-line border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-xl font-bold tracking-tight text-gray-900 dark:text-white">
          <img src={import.meta.env.BASE_URL + 'logo.svg'} alt="Athene" className="h-8 w-8" />
          <span className="tech-heading">Athene</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden items-center gap-2 md:flex">
          <nav className="flex gap-1">
            {NAV_ITEMS.map(({ path, label }) => {
              const active = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    active
                      ? 'tech-nav-active bg-gray-900 text-white dark:bg-transparent'
                      : 'tech-nav-item text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-transparent'
                  }`}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
          <a
            href={import.meta.env.BASE_URL + 'data/feed.xml'}
            target="_blank"
            rel="noopener noreferrer"
            className="tech-ctrl rounded-md border border-gray-200 px-2 py-1 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            aria-label="RSS Feed"
            title="RSS"
          >
            RSS
          </a>
          <button
            onClick={toggle}
            className="tech-ctrl rounded-md border border-gray-200 px-2 py-1 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            aria-label="Toggle dark mode"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            onClick={() => setLocale(locale === 'en' ? 'zh' : 'en')}
            className="tech-ctrl rounded-md border border-gray-200 px-2 py-1 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            {locale === 'en' ? '中文' : 'EN'}
          </button>
        </div>

        {/* Mobile: utility buttons + hamburger */}
        <div className="flex items-center gap-1 md:hidden">
          <button
            onClick={toggle}
            className="tech-ctrl rounded-md border border-gray-200 p-2 text-sm text-gray-600 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            aria-label="Toggle dark mode"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            onClick={() => setLocale(locale === 'en' ? 'zh' : 'en')}
            className="tech-ctrl rounded-md border border-gray-200 px-2 py-2 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            {locale === 'en' ? '中文' : 'EN'}
          </button>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="tech-ctrl rounded-md border border-gray-200 p-2 text-gray-600 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            aria-label="Toggle menu"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              {menuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile slide-down menu */}
      {menuOpen && (
        <nav className="tech-bar border-t border-gray-200 bg-white px-4 pb-3 pt-2 md:hidden dark:border-gray-700 dark:bg-gray-800">
          <div className="flex flex-col gap-1">
            {NAV_ITEMS.map(({ path, label }) => {
              const active = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  onClick={() => setMenuOpen(false)}
                  className={`rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                    active
                      ? 'tech-nav-active bg-gray-900 text-white dark:bg-transparent'
                      : 'tech-nav-item text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-transparent'
                  }`}
                >
                  {label}
                </Link>
              );
            })}
            <a
              href={import.meta.env.BASE_URL + 'data/feed.xml'}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => setMenuOpen(false)}
              className="tech-nav-item rounded-md px-3 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-transparent"
            >
              RSS Feed
            </a>
          </div>
        </nav>
      )}
    </header>
  );
}
