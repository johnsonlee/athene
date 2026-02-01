import { useI18n } from '../lib/i18n';

export function About() {
  const { t } = useI18n();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">{t('about.title')}</h1>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">{t('about.methodology')}</h2>
        <p className="text-sm text-gray-600">{t('about.methodologyDesc')}</p>

        <h3 className="mt-4 font-semibold">{t('about.multiFactorModel')}</h3>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-1">{t('about.factor')}</th>
              <th className="py-1">{t('about.weight')}</th>
              <th className="py-1">{t('about.components')}</th>
            </tr>
          </thead>
          <tbody className="text-gray-600">
            <tr className="border-b">
              <td className="py-1 font-medium">{t('detail.fundamentals')}</td>
              <td>40%</td>
              <td>{t('about.fundComponents')}</td>
            </tr>
            <tr className="border-b">
              <td className="py-1 font-medium">{t('detail.technical')}</td>
              <td>35%</td>
              <td>{t('about.techComponents')}</td>
            </tr>
            <tr>
              <td className="py-1 font-medium">{t('detail.sentiment')}</td>
              <td>25%</td>
              <td>{t('about.sentComponents')}</td>
            </tr>
          </tbody>
        </table>

        <h3 className="mt-4 font-semibold">{t('about.ratingTiers')}</h3>
        <ul className="mt-2 space-y-1 text-sm text-gray-600">
          <li><strong>{t('tier.strong_buy')}</strong> (Top 10%) - {t('about.tierStrongBuy')}</li>
          <li><strong>{t('tier.buy')}</strong> (10-30%) - {t('about.tierBuy')}</li>
          <li><strong>{t('tier.hold')}</strong> (30-70%) - {t('about.tierHold')}</li>
          <li><strong>{t('tier.sell')}</strong> (70-90%) - {t('about.tierSell')}</li>
          <li><strong>{t('tier.strong_sell')}</strong> (Bottom 10%) - {t('about.tierStrongSell')}</li>
        </ul>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">{t('about.dataSources')}</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-600">
          <li>Price data &amp; fundamentals: Yahoo Finance (via yfinance)</li>
          <li>News headlines: Yahoo Finance / Finviz</li>
          <li>Stock universe: Wikipedia (S&amp;P 500 + NASDAQ 100 lists)</li>
        </ul>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">{t('about.disclaimer')}</h2>
        <p className="text-sm text-gray-600">{t('about.disclaimerText')}</p>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">RSS Feed</h2>
        <p className="text-sm text-gray-600">
          <a href="/data/feed.xml" className="text-blue-600 hover:underline">
            https://athene.johnsonlee.io/data/feed.xml
          </a>
        </p>
      </section>
    </div>
  );
}
