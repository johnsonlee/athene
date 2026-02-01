import { createContext, useContext, useState, type ReactNode } from 'react';

export type Locale = 'en' | 'zh';

const translations = {
  en: {
    // Nav
    'nav.dashboard': 'Dashboard',
    'nav.screener': 'Screener',
    'nav.about': 'About',

    // Dashboard
    'dashboard.title': 'Market Overview',
    'dashboard.analyzed': '{count} stocks analyzed',
    'dashboard.top10': 'Top 10',
    'dashboard.bottom10': 'Bottom 10',
    'dashboard.sectorOverview': 'Sector Overview',
    'dashboard.scoreDistribution': 'Score Distribution',
    'dashboard.stocks': '{count} stocks',

    // Screener
    'screener.title': 'Stock Screener',
    'screener.showing': '{filtered} of {total} stocks',
    'screener.exportCsv': 'Export CSV',
    'screener.searchPlaceholder': 'Search ticker or name...',
    'screener.allSectors': 'All Sectors',
    'screener.reset': 'Reset',
    'screener.prev': 'Prev',
    'screener.next': 'Next',
    'screener.page': 'Page {current} of {total}',

    // Table headers
    'table.rank': '#',
    'table.ticker': 'Ticker',
    'table.name': 'Name',
    'table.sector': 'Sector',
    'table.score': 'Score',
    'table.fundamental': 'Fund.',
    'table.technical': 'Tech.',
    'table.sentiment': 'Sent.',
    'table.rating': 'Rating',

    // Tiers
    'tier.strong_buy': 'Strong Buy',
    'tier.buy': 'Buy',
    'tier.hold': 'Hold',
    'tier.sell': 'Sell',
    'tier.strong_sell': 'Strong Sell',

    // Stock Detail
    'detail.backToScreener': 'Back to Screener',
    'detail.rank': 'Rank #{rank}',
    'detail.priceChart': '{ticker} Price Chart',
    'detail.ratingAnalysis': 'Rating Analysis',
    'detail.ratedAs': '{ticker} is rated {tier} (rank #{rank}, top {pct}) with a composite score of {score}.',
    'detail.signalSummary': 'The analysis found {bullish} bullish and {bearish} bearish signals across {total} indicators.',
    'detail.factorScores': 'Factor Scores',
    'detail.fundamentals': 'Fundamentals',
    'detail.technical': 'Technical',
    'detail.sentiment': 'Sentiment',
    'detail.noData': 'No data available',
    'detail.recentNews': 'Recent News',
    'detail.weight': 'Weight: {weight}',
    'detail.volume': 'Volume',
    'detail.noFactorData': 'No data available for this factor',
    'detail.articles': '{count} articles',

    // Factor names (for radar chart)
    'factor.value': 'Value',
    'factor.quality': 'Quality',
    'factor.growth': 'Growth',
    'factor.safety': 'Safety',
    'factor.trend': 'Trend',
    'factor.momentum': 'Momentum',
    'factor.volatility': 'Volatility',
    'factor.volume': 'Volume',

    // Chart labels
    'chart.rsi14': 'RSI (14)',
    'chart.macd1226': 'MACD (12, 26, 9)',
    'chart.stochastic': 'Stochastic (14, 3, 3)',
    'chart.signal': 'Signal',
    'chart.histogram': 'Histogram',
    'chart.bollingerBands': 'Bollinger Bands',
    'chart.hist': 'Hist',

    // Metric group headers
    'group.valuation': 'Valuation',
    'group.profitability': 'Profitability',
    'group.growth': 'Growth',
    'group.balanceSheet': 'Balance Sheet',
    'group.market': 'Market',
    'group.trend': 'Trend',
    'group.momentum': 'Momentum',
    'group.volatility': 'Volatility',
    'group.volumeActivity': 'Volume',
    'group.sentimentBreakdown': 'Sentiment Breakdown',

    // Fundamental labels
    'metric.pe': 'P/E',
    'metric.fwdPe': 'Fwd P/E',
    'metric.pb': 'P/B',
    'metric.ps': 'P/S',
    'metric.roe': 'ROE',
    'metric.roa': 'ROA',
    'metric.revGrowth': 'Rev Growth',
    'metric.earnGrowth': 'Earn Growth',
    'metric.debtEquity': 'Debt/Equity',
    'metric.marketCap': 'Market Cap',
    'metric.profitMargin': 'Profit Margin',
    'metric.divYield': 'Dividend Yield',
    'metric.beta': 'Beta',
    'metric.52wHigh': '52W High',
    'metric.52wLow': '52W Low',
    'metric.rsi': 'RSI',
    'metric.macd': 'MACD',
    'metric.macdHist': 'MACD Hist',
    'metric.sma20': 'SMA 20',
    'metric.sma50': 'SMA 50',
    'metric.sma200': 'SMA 200',
    'metric.bbPosition': 'BB Position',
    'metric.trendAlignment': 'Trend Alignment',
    'metric.volRatio': 'Vol Ratio',
    'metric.stochK': 'Stoch K',
    'metric.stochD': 'Stoch D',
    'metric.compound': 'Compound',
    'metric.positive': 'Positive',
    'metric.negative': 'Negative',
    'metric.neutral': 'Neutral',
    'metric.newsCount': 'News Count',
    'metric.newsSentiment': 'News Sentiment',
    'metric.newsVolume': 'News Volume',

    // Score breakdown drivers
    'driver.pe.bullish': 'Low valuation relative to earnings',
    'driver.pe.bearish': 'High valuation relative to earnings',
    'driver.pe.neutral': 'Moderate valuation',
    'driver.roe.bullish': 'Strong return on equity',
    'driver.roe.bearish': 'Weak return on equity',
    'driver.roe.neutral': 'Average return on equity',
    'driver.revGrowth.bullish': 'Strong revenue growth',
    'driver.revGrowth.bearish': 'Revenue declining',
    'driver.revGrowth.neutral': 'Modest revenue growth',
    'driver.earnGrowth.bullish': 'Strong earnings growth',
    'driver.earnGrowth.bearish': 'Earnings declining',
    'driver.earnGrowth.neutral': 'Modest earnings growth',
    'driver.debt.bullish': 'Low leverage, strong balance sheet',
    'driver.debt.bearish': 'High leverage, financial risk',
    'driver.debt.neutral': 'Moderate leverage',
    'driver.margin.bullish': 'High profitability',
    'driver.margin.bearish': 'Low profitability',
    'driver.margin.neutral': 'Average profitability',
    'driver.trend.bullish': 'Price above key moving averages (bullish trend)',
    'driver.trend.bearish': 'Price below key moving averages (bearish trend)',
    'driver.trend.neutral': 'Mixed trend signals',
    'driver.rsi.overbought': 'Overbought territory, potential pullback',
    'driver.rsi.oversold': 'Oversold territory, potential bounce',
    'driver.rsi.positive': 'Positive momentum',
    'driver.rsi.weak': 'Weak momentum',
    'driver.macd.bullish': 'Positive MACD momentum',
    'driver.macd.bearish': 'Negative MACD momentum',
    'driver.bb.high': 'Near upper band, potentially overextended',
    'driver.bb.low': 'Near lower band, potentially oversold',
    'driver.bb.normal': 'Within normal trading range',
    'driver.vol.high': 'Above average volume, strong interest',
    'driver.vol.low': 'Below average volume, low interest',
    'driver.vol.normal': 'Normal volume',
    'driver.sentiment.bullish': 'Positive news sentiment overall',
    'driver.sentiment.bearish': 'Negative news sentiment overall',
    'driver.sentiment.neutral': 'Neutral news sentiment',
    'driver.newsVolume': 'Based on {count} recent news articles',

    // About page
    'about.title': 'About Athene',
    'about.methodology': 'Methodology',
    'about.methodologyDesc': 'Athene is a quantitative stock screening engine that combines three analysis dimensions into a composite score for each stock in the S&P 500 + NASDAQ 100 universe (~550 stocks).',
    'about.multiFactorModel': 'Multi-Factor Model',
    'about.factor': 'Factor',
    'about.weight': 'Weight',
    'about.components': 'Components',
    'about.fundComponents': 'Value (PE/PB/PS), Quality (ROE/ROA), Growth (revenue/earnings), Safety (D/E, FCF)',
    'about.techComponents': 'Trend (MA alignment), Momentum (MACD/RSI), Volatility (Bollinger), Volume ratio',
    'about.sentComponents': 'VADER sentiment analysis on recent news headlines',
    'about.ratingTiers': 'Rating Tiers',
    'about.tierStrongBuy': 'Highest composite scores',
    'about.tierBuy': 'Above average on most factors',
    'about.tierHold': 'Average composite scores',
    'about.tierSell': 'Below average scores',
    'about.tierStrongSell': 'Lowest composite scores',
    'about.dataSources': 'Data Sources',
    'about.dataPrice': 'Price data & fundamentals: Yahoo Finance (via yfinance)',
    'about.dataNews': 'News headlines: Yahoo Finance / Finviz',
    'about.dataUniverse': 'Stock universe: Wikipedia (S&P 500 + NASDAQ 100 lists)',
    'about.rssFeed': 'RSS Feed',
    'about.disclaimer': 'Disclaimer',
    'about.disclaimerText': 'This tool is for educational and informational purposes only. It does not constitute financial advice, investment recommendations, or solicitation to buy or sell any securities. Past performance does not guarantee future results. Always conduct your own research and consult with a qualified financial advisor before making investment decisions. The authors are not responsible for any financial losses resulting from the use of this tool.',

    // Footer
    'footer.dataFrom': 'Data from Yahoo Finance',
    'footer.lastUpdated': 'Last updated: {date}',
    'footer.stockCount': '{count} stocks',
    'footer.disclaimer': 'For educational purposes only. Not financial advice.',

    // Common
    'common.loading': 'Loading...',
    'common.error': 'Error: {message}',
    'common.noDataFound': 'No data found',
  },

  zh: {
    // Nav
    'nav.dashboard': '市场概览',
    'nav.screener': '选股器',
    'nav.about': '关于',

    // Dashboard
    'dashboard.title': '市场概览',
    'dashboard.analyzed': '已分析 {count} 只股票',
    'dashboard.top10': '涨幅前10',
    'dashboard.bottom10': '跌幅前10',
    'dashboard.sectorOverview': '板块概览',
    'dashboard.scoreDistribution': '得分分布',
    'dashboard.stocks': '{count} 只股票',

    // Screener
    'screener.title': '股票筛选器',
    'screener.showing': '共 {total} 只，显示 {filtered} 只',
    'screener.exportCsv': '导出 CSV',
    'screener.searchPlaceholder': '搜索代码或名称...',
    'screener.allSectors': '全部板块',
    'screener.reset': '重置',
    'screener.prev': '上一页',
    'screener.next': '下一页',
    'screener.page': '第 {current} 页，共 {total} 页',

    // Table headers
    'table.rank': '排名',
    'table.ticker': '代码',
    'table.name': '名称',
    'table.sector': '板块',
    'table.score': '综合得分',
    'table.fundamental': '基本面',
    'table.technical': '技术面',
    'table.sentiment': '舆情',
    'table.rating': '评级',

    // Tiers
    'tier.strong_buy': '强烈推荐',
    'tier.buy': '推荐',
    'tier.hold': '持有',
    'tier.sell': '减持',
    'tier.strong_sell': '强烈减持',

    // Stock Detail
    'detail.backToScreener': '返回选股器',
    'detail.rank': '排名 #{rank}',
    'detail.priceChart': '{ticker} 价格走势',
    'detail.ratingAnalysis': '评级分析',
    'detail.ratedAs': '{ticker} 被评为 {tier}（排名 #{rank}，前 {pct}），综合得分 {score}。',
    'detail.signalSummary': '分析发现 {bullish} 个看涨信号和 {bearish} 个看跌信号，共分析 {total} 个指标。',
    'detail.factorScores': '因子得分',
    'detail.fundamentals': '基本面',
    'detail.technical': '技术面',
    'detail.sentiment': '舆情',
    'detail.noData': '暂无数据',
    'detail.recentNews': '近期新闻',
    'detail.weight': '权重：{weight}',
    'detail.volume': '成交量',
    'detail.noFactorData': '该因子暂无数据',
    'detail.articles': '{count} 篇文章',

    // Factor names (for radar chart)
    'factor.value': '价值',
    'factor.quality': '质量',
    'factor.growth': '成长',
    'factor.safety': '安全',
    'factor.trend': '趋势',
    'factor.momentum': '动量',
    'factor.volatility': '波动',
    'factor.volume': '量能',

    // Chart labels
    'chart.rsi14': 'RSI (14)',
    'chart.macd1226': 'MACD (12, 26, 9)',
    'chart.stochastic': '随机指标 (14, 3, 3)',
    'chart.signal': '信号线',
    'chart.histogram': '柱状图',
    'chart.bollingerBands': '布林带',
    'chart.hist': '柱',

    // Metric group headers
    'group.valuation': '估值',
    'group.profitability': '盈利能力',
    'group.growth': '成长性',
    'group.balanceSheet': '资产负债',
    'group.market': '市场',
    'group.trend': '趋势',
    'group.momentum': '动量',
    'group.volatility': '波动性',
    'group.volumeActivity': '成交量',
    'group.sentimentBreakdown': '情绪分布',

    // Fundamental labels
    'metric.pe': '市盈率',
    'metric.fwdPe': '预期市盈率',
    'metric.pb': '市净率',
    'metric.ps': '市销率',
    'metric.roe': '净资产收益率',
    'metric.roa': '总资产收益率',
    'metric.revGrowth': '营收增长',
    'metric.earnGrowth': '盈利增长',
    'metric.debtEquity': '资产负债率',
    'metric.marketCap': '总市值',
    'metric.profitMargin': '利润率',
    'metric.divYield': '股息率',
    'metric.beta': 'Beta',
    'metric.52wHigh': '52周最高',
    'metric.52wLow': '52周最低',
    'metric.rsi': 'RSI',
    'metric.macd': 'MACD',
    'metric.macdHist': 'MACD 柱',
    'metric.sma20': '20日均线',
    'metric.sma50': '50日均线',
    'metric.sma200': '200日均线',
    'metric.bbPosition': '布林带位置',
    'metric.trendAlignment': '趋势一致性',
    'metric.volRatio': '量比',
    'metric.stochK': '随机指标 K',
    'metric.stochD': '随机指标 D',
    'metric.compound': '综合情绪',
    'metric.positive': '正面',
    'metric.negative': '负面',
    'metric.neutral': '中性',
    'metric.newsCount': '新闻数量',
    'metric.newsSentiment': '新闻情绪',
    'metric.newsVolume': '新闻量',

    // Score breakdown drivers
    'driver.pe.bullish': '相对盈利估值较低',
    'driver.pe.bearish': '相对盈利估值较高',
    'driver.pe.neutral': '估值适中',
    'driver.roe.bullish': '净资产收益率高',
    'driver.roe.bearish': '净资产收益率低',
    'driver.roe.neutral': '净资产收益率一般',
    'driver.revGrowth.bullish': '营收增长强劲',
    'driver.revGrowth.bearish': '营收下滑',
    'driver.revGrowth.neutral': '营收温和增长',
    'driver.earnGrowth.bullish': '盈利增长强劲',
    'driver.earnGrowth.bearish': '盈利下滑',
    'driver.earnGrowth.neutral': '盈利温和增长',
    'driver.debt.bullish': '低杠杆，资产负债表稳健',
    'driver.debt.bearish': '高杠杆，有财务风险',
    'driver.debt.neutral': '杠杆适中',
    'driver.margin.bullish': '盈利能力强',
    'driver.margin.bearish': '盈利能力弱',
    'driver.margin.neutral': '盈利能力一般',
    'driver.trend.bullish': '价格在关键均线上方（多头趋势）',
    'driver.trend.bearish': '价格在关键均线下方（空头趋势）',
    'driver.trend.neutral': '趋势信号混合',
    'driver.rsi.overbought': '超买区域，可能回调',
    'driver.rsi.oversold': '超卖区域，可能反弹',
    'driver.rsi.positive': '动量向上',
    'driver.rsi.weak': '动量偏弱',
    'driver.macd.bullish': 'MACD 动量为正',
    'driver.macd.bearish': 'MACD 动量为负',
    'driver.bb.high': '接近上轨，可能过度延伸',
    'driver.bb.low': '接近下轨，可能超卖',
    'driver.bb.normal': '在正常交易区间内',
    'driver.vol.high': '高于平均成交量，关注度高',
    'driver.vol.low': '低于平均成交量，关注度低',
    'driver.vol.normal': '成交量正常',
    'driver.sentiment.bullish': '新闻舆情整体偏正面',
    'driver.sentiment.bearish': '新闻舆情整体偏负面',
    'driver.sentiment.neutral': '新闻舆情中性',
    'driver.newsVolume': '基于 {count} 篇近期新闻',

    // About page
    'about.title': '关于 Athene',
    'about.methodology': '分析方法',
    'about.methodologyDesc': 'Athene 是一个量化选股引擎，将三个分析维度综合为每只股票的复合得分，覆盖标普500和纳斯达克100指数成分股（约550只）。',
    'about.multiFactorModel': '多因子模型',
    'about.factor': '因子',
    'about.weight': '权重',
    'about.components': '组成',
    'about.fundComponents': '价值（PE/PB/PS）、质量（ROE/ROA）、成长（营收/盈利增长）、安全（负债率/FCF）',
    'about.techComponents': '趋势（均线排列）、动量（MACD/RSI）、波动（布林带）、量能',
    'about.sentComponents': '基于新闻标题的 VADER 情感分析',
    'about.ratingTiers': '评级等级',
    'about.tierStrongBuy': '综合得分最高',
    'about.tierBuy': '大多数因子优于平均',
    'about.tierHold': '综合得分居中',
    'about.tierSell': '得分低于平均',
    'about.tierStrongSell': '综合得分最低',
    'about.dataSources': '数据来源',
    'about.dataPrice': '行情和基本面数据：Yahoo Finance (yfinance)',
    'about.dataNews': '新闻标题：Yahoo Finance / Finviz',
    'about.dataUniverse': '股票池：维基百科（标普500 + 纳斯达克100列表）',
    'about.rssFeed': 'RSS 订阅',
    'about.disclaimer': '免责声明',
    'about.disclaimerText': '本工具仅供教育和信息参考之用。不构成财务建议、投资推荐或买卖任何证券的招揽。过去的表现不保证未来的结果。在做出投资决策前，请始终进行自己的研究并咨询合格的财务顾问。作者不对因使用本工具造成的任何财务损失负责。',

    // Footer
    'footer.dataFrom': '数据来自 Yahoo Finance',
    'footer.lastUpdated': '最后更新：{date}',
    'footer.stockCount': '{count} 只股票',
    'footer.disclaimer': '仅供教育参考，不构成投资建议。',

    // Common
    'common.loading': '加载中...',
    'common.error': '错误：{message}',
    'common.noDataFound': '未找到数据',
  },
} as const;

type TranslationKey = keyof typeof translations.en;

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue>(null!);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => {
    const saved = localStorage.getItem('athene-locale');
    if (saved === 'en' || saved === 'zh') return saved;
    return navigator.language.startsWith('zh') ? 'zh' : 'en';
  });

  const changeLocale = (l: Locale) => {
    setLocale(l);
    localStorage.setItem('athene-locale', l);
  };

  const t = (key: TranslationKey, params?: Record<string, string | number>): string => {
    let text: string = translations[locale][key] ?? translations.en[key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        text = text.replace(`{${k}}`, String(v));
      }
    }
    return text;
  };

  return (
    <I18nContext.Provider value={{ locale, setLocale: changeLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
