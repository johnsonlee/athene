import { createBrowserRouter } from 'react-router-dom';
import { App } from './App';
import { TrendDashboard } from './components/trends/TrendDashboard';
import { Dashboard } from './components/dashboard/Dashboard';
import { ScreenerPage } from './components/screener/ScreenerPage';
import { StockDetailPage } from './components/detail/StockDetailPage';
import { About } from './components/About';

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <App />,
      children: [
        { index: true, element: <TrendDashboard /> },
        { path: 'dashboard', element: <Dashboard /> },
        { path: 'screener', element: <ScreenerPage /> },
        { path: 'stock/:ticker', element: <StockDetailPage /> },
        { path: 'about', element: <About /> },
      ],
    },
  ],
  { basename: '/' }
);
