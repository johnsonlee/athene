export function About() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">About Athene</h1>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Methodology</h2>
        <p className="text-sm text-gray-600">
          Athene is a quantitative stock screening engine that combines three analysis dimensions
          into a composite score for each stock in the S&amp;P 500 + NASDAQ 100 universe (~550 stocks).
        </p>

        <h3 className="mt-4 font-semibold">Multi-Factor Model</h3>
        <table className="mt-2 w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-1">Factor</th>
              <th className="py-1">Weight</th>
              <th className="py-1">Components</th>
            </tr>
          </thead>
          <tbody className="text-gray-600">
            <tr className="border-b">
              <td className="py-1 font-medium">Fundamental</td>
              <td>40%</td>
              <td>Value (PE/PB/PS), Quality (ROE/ROA), Growth (revenue/earnings), Safety (D/E, FCF)</td>
            </tr>
            <tr className="border-b">
              <td className="py-1 font-medium">Technical</td>
              <td>35%</td>
              <td>Trend (MA alignment), Momentum (MACD/RSI), Volatility (Bollinger), Volume ratio</td>
            </tr>
            <tr>
              <td className="py-1 font-medium">Sentiment</td>
              <td>25%</td>
              <td>VADER sentiment analysis on recent news headlines</td>
            </tr>
          </tbody>
        </table>

        <h3 className="mt-4 font-semibold">Rating Tiers</h3>
        <ul className="mt-2 space-y-1 text-sm text-gray-600">
          <li><strong>Strong Buy</strong> (Top 10%) - Highest composite scores</li>
          <li><strong>Buy</strong> (10-30%) - Above average on most factors</li>
          <li><strong>Hold</strong> (30-70%) - Average composite scores</li>
          <li><strong>Sell</strong> (70-90%) - Below average scores</li>
          <li><strong>Strong Sell</strong> (Bottom 10%) - Lowest composite scores</li>
        </ul>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Data Sources</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-600">
          <li>Price data & fundamentals: Yahoo Finance (via yfinance)</li>
          <li>News headlines: Yahoo Finance / Finviz</li>
          <li>Stock universe: Wikipedia (S&amp;P 500 + NASDAQ 100 lists)</li>
        </ul>
      </section>

      <section className="rounded-lg bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Disclaimer</h2>
        <p className="text-sm text-gray-600">
          This tool is for <strong>educational and informational purposes only</strong>.
          It does not constitute financial advice, investment recommendations, or solicitation
          to buy or sell any securities. Past performance does not guarantee future results.
          Always conduct your own research and consult with a qualified financial advisor
          before making investment decisions. The authors are not responsible for any
          financial losses resulting from the use of this tool.
        </p>
      </section>
    </div>
  );
}
