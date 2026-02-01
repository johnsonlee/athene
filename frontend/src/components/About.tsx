import { useI18n } from '../lib/i18n';

export function About() {
  const { t } = useI18n();

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('about.title')}</h1>

      <section className="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.methodology')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('about.methodologyDesc')}</p>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.multiFactorModel')}</h3>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b text-left dark:border-gray-700">
              <th className="py-1 text-gray-900 dark:text-white">{t('about.factor')}</th>
              <th className="py-1 text-gray-900 dark:text-white">{t('about.weight')}</th>
              <th className="py-1 text-gray-900 dark:text-white">{t('about.components')}</th>
            </tr>
          </thead>
          <tbody className="text-gray-600 dark:text-gray-400">
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.fundamentals')}</td>
              <td>50%</td>
              <td>{t('about.fundComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.fundSubWeights')}</span></td>
            </tr>
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.technical')}</td>
              <td>30%</td>
              <td>{t('about.techComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.techSubWeights')}</span></td>
            </tr>
            <tr>
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('detail.sentiment')}</td>
              <td>20%</td>
              <td>{t('about.sentComponents')}<br /><span className="text-xs text-gray-400 dark:text-gray-500">{t('about.sentSubWeights')}</span></td>
            </tr>
          </tbody>
        </table>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.scoringTitle')}</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringAbsolute')}</p>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringComposite')}</p>
        <p className="mt-1 rounded bg-gray-100 px-3 py-2 font-mono text-sm text-gray-800 dark:bg-gray-900 dark:text-gray-200">{t('about.scoringFormula')}</p>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.scoringSmoothing')}</p>

        <h3 className="mt-4 font-semibold text-gray-900 dark:text-white">{t('about.ratingTiers')}</h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{t('about.ratingTiersDesc')}</p>
        <table className="mt-2 w-full text-sm">
          <tbody className="text-gray-600 dark:text-gray-400">
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.strong_buy')}</td>
              <td>{t('about.tierStrongBuy')}</td>
            </tr>
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.buy')}</td>
              <td>{t('about.tierBuy')}</td>
            </tr>
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.hold')}</td>
              <td>{t('about.tierHold')}</td>
            </tr>
            <tr className="border-b dark:border-gray-700">
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.sell')}</td>
              <td>{t('about.tierSell')}</td>
            </tr>
            <tr>
              <td className="py-1 font-medium text-gray-800 dark:text-gray-200">{t('tier.strong_sell')}</td>
              <td>{t('about.tierStrongSell')}</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t('about.hysteresis')}</p>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.dataSources')}</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>{t('about.dataPrice')}</li>
          <li>{t('about.dataNews')}</li>
          <li>{t('about.dataUniverse')}</li>
        </ul>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.disclaimer')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('about.disclaimerText')}</p>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm dark:bg-gray-800">
        <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{t('about.rssFeed')}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          <a href="/data/feed.xml" className="text-blue-600 hover:underline dark:text-blue-400">
            https://athene.johnsonlee.io/data/feed.xml
          </a>
        </p>
      </section>
    </div>
  );
}
