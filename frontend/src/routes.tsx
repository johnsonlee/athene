import { createBrowserRouter } from 'react-router-dom';
import { App } from './App';
import { TrendDashboard } from './components/trends/TrendDashboard';
import { Dashboard } from './components/dashboard/Dashboard';
import { ScreenerPage } from './components/screener/ScreenerPage';
import { StockDetailPage } from './components/detail/StockDetailPage';
import { CapitalFlowViz } from './components/flows/CapitalFlowViz';
import { About } from './components/About';
import { BacktestPage } from './components/backtest/BacktestPage';
import { LeadingIndicatorsPage } from './components/indicators/LeadingIndicatorsPage';

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <App />,
      children: [
        { index: true, element: <CapitalFlowViz /> },
        { path: 'flows', element: <CapitalFlowViz /> },
        { path: 'trends', element: <TrendDashboard /> },
        { path: 'indicators', element: <LeadingIndicatorsPage /> },
        { path: 'dashboard', element: <Dashboard /> },
        { path: 'screener', element: <ScreenerPage /> },
        { path: 'stock/:ticker', element: <StockDetailPage /> },
        { path: 'backtest', element: <BacktestPage /> },
        { path: 'about', element: <About /> },
      ],
    },
  ],
  { basename: '/' }
);
